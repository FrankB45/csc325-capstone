import base64
import binascii
import json
import posixpath
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

import requests

from .github import (
    _get_default_branch_tree_sha,
    get_repository_information,
    parse_github_url,
    github_headers,
)

# These file-blob limits leave existing metadata/tree retrieval behavior unchanged.
MAX_PROFILE_FILE_BYTES = 2 * 1024 * 1024
MAX_PROFILE_CONTENT_BYTES = 8 * 1024 * 1024
MAX_PROFILE_DOWNLOAD_BYTES = 16 * 1024 * 1024


class _StaticHomepageParser(HTMLParser):
    """Collect direct resources without judging browser markup or script behavior."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.resources = []
        self.has_base_url = False

    def handle_starttag(self, tag, attributes):
        values = {}
        for name, value in attributes:
            if name in values:
                # Conflicting attributes do not establish a definitely missing file.
                values[name] = None
            else:
                values[name] = value
        if tag == "base" and "href" in values:
            self.has_base_url = True
        if tag in {"script", "img", "source", "video", "audio", "iframe", "input"}:
            if "src" in values:
                self.resources.append(values["src"])
        elif tag == "link":
            relations = (values.get("rel") or "").lower().split()
            for relation in relations:
                if relation in {"stylesheet", "icon", "preload", "modulepreload"}:
                    self.resources.append(values.get("href"))
                    break

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)


class _HomepageParser(HTMLParser):
    """Recognize only a simple, otherwise empty page with one startup module."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.is_supported = True
        self.open_tags = []
        self.seen_tags = set()
        self.startup_source = None

    def handle_starttag(self, tag, attributes):
        attribute_values = {}
        for name, value in attributes:
            if name in attribute_values or value is None:
                self.is_supported = False
            attribute_values[name] = value
        if not self.is_supported:
            return

        parent = None
        if self.open_tags:
            parent = self.open_tags[-1]

        if tag == "html":
            if parent is not None or tag in self.seen_tags:
                self.is_supported = False
            if set(attribute_values) - {"lang"}:
                self.is_supported = False
        elif tag == "head":
            if parent != "html" or tag in self.seen_tags or "body" in self.seen_tags:
                self.is_supported = False
            if attributes:
                self.is_supported = False
        elif tag == "body":
            if parent != "html" or tag in self.seen_tags or "head" not in self.seen_tags:
                self.is_supported = False
            if attributes:
                self.is_supported = False
        elif tag == "meta":
            if parent != "head":
                self.is_supported = False
            if set(attribute_values) == {"charset"}:
                if attribute_values["charset"].lower() not in ("utf-8", "utf8"):
                    self.is_supported = False
            elif set(attribute_values) == {"name", "content"}:
                if attribute_values["name"] != "viewport":
                    self.is_supported = False
            else:
                self.is_supported = False
            return
        elif tag == "title":
            if parent != "head" or tag in self.seen_tags or attributes:
                self.is_supported = False
        elif tag == "div":
            if parent != "body" or tag in self.seen_tags:
                self.is_supported = False
            if set(attribute_values) != {"id"} or not attribute_values.get("id"):
                self.is_supported = False
        elif tag == "script":
            if parent not in ("head", "body") or tag in self.seen_tags:
                self.is_supported = False
            if set(attribute_values) != {"type", "src"}:
                self.is_supported = False
            if attribute_values.get("type") != "module":
                self.is_supported = False
            self.startup_source = attribute_values.get("src")
        else:
            # Other elements may supply content, styling, loaders or a base URL.
            self.is_supported = False

        self.seen_tags.add(tag)
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if not self.open_tags or self.open_tags[-1] != tag:
            self.is_supported = False
            return
        self.open_tags.pop()

    def handle_startendtag(self, tag, attributes):
        if tag == "meta":
            self.handle_starttag(tag, attributes)
        else:
            self.is_supported = False

    def handle_data(self, data):
        if data.strip(" \t\r\n\f") and self.open_tags[-1:] != ["title"]:
            self.is_supported = False

    def handle_decl(self, declaration):
        if declaration.lower() != "doctype html" or self.seen_tags:
            self.is_supported = False

    def handle_pi(self, data):
        self.is_supported = False

    def unknown_decl(self, data):
        self.is_supported = False


def check_repository_dependencies(
    repo_url: str,
    *,
    tree_sha: str | None = None,
) -> dict:
    """Check static-hosting prerequisites, not JavaScript behavior or rendering.

    This limited policy cannot detect every undeclared backend or build requirement.
    """
    result = {
        "dependency_status": "pending",
        "reason": "This limited check has not established an unsupported dependency.",
        "evidence_paths": [],
        "tree_sha": None,
    }
    try:
        owner, repo = parse_github_url(repo_url)
    except ValueError:
        result["reason"] = "A valid repository URL is needed before checking dependencies."
        return result

    try:
        if tree_sha is None:
            repository = get_repository_information(repo_url)
            default_branch = repository["default_branch"]
            if default_branch is None:
                result["reason"] = "There is no usable default branch to inspect for dependencies."
                return result
            if not isinstance(default_branch, str):
                raise ValueError("GitHub returned invalid default-branch information.")
            if not default_branch.strip():
                result["reason"] = "There is no usable default branch to inspect for dependencies."
                return result

            tree_sha = _get_default_branch_tree_sha(owner, repo, default_branch)
            
        result["tree_sha"] = tree_sha
        files = _get_snapshot_files(owner, repo, tree_sha)
        homepage_paths = []
        for path in files:
            if path.lower() == "index.html":
                homepage_paths.append(path)
        if len(homepage_paths) != 1:
            result["reason"] = "One unambiguous regular root index.html is needed for this check."
            return result

        homepage_path = homepage_paths[0]
        result["evidence_paths"] = [homepage_path]
        budget = {"content_bytes": 0, "download_bytes": 0, "limit_reason": ""}
        declaration_result = _check_backend_declaration(owner, repo, files, tree_sha, budget)
        if declaration_result is not None:
            if declaration_result["dependency_status"] == "rejected" or budget["limit_reason"]:
                return declaration_result
        homepage_text = _read_snapshot_text(owner, repo, files[homepage_path], budget)
        if homepage_text is None:
            result["reason"] = budget["limit_reason"]
            return result
        # Keep the narrow startup rejection before the more permissive static check.
        homepage = _HomepageParser()
        try:
            homepage.feed(homepage_text)
            homepage.close()
        except (AssertionError, ValueError):
            homepage.is_supported = False

        startup_path = None
        required_tags = {"html", "head", "body", "div", "script"}
        if (
            homepage.is_supported
            and not homepage.open_tags
            and required_tags.issubset(homepage.seen_tags)
            and homepage.startup_source
        ):
            source = homepage.startup_source
            try:
                source_url = urlsplit(source)
            except ValueError:
                source_url = None
            if source_url is not None and not (
                source_url.scheme
                or source_url.netloc
                or source_url.query
                or source_url.fragment
                or "\\" in source
                or "%" in source
                or any(ord(character) < 32 or character.isspace() for character in source)
            ):
                local_path = source_url.path
                if local_path.startswith("./"):
                    local_path = local_path[2:]
                elif local_path.startswith("/"):
                    local_path = local_path[1:]
                if local_path and not any(part in ("", ".", "..") for part in local_path.split("/")):
                    startup_path = local_path

        if startup_path is not None:
            if startup_path not in files:
                result["reason"] = (
                    f"Startup file '{startup_path}' is missing or is not a regular file. "
                    "That alone does not establish an unsupported dependency."
                )
                return result
            result["evidence_paths"].append(startup_path)
            startup_text = _read_snapshot_text(owner, repo, files[startup_path], budget)
            if startup_text is None:
                result["reason"] = budget["limit_reason"]
                return result
            package = _find_unresolved_startup_import(startup_text)
            if package is not None:
                result["dependency_status"] = "rejected"
                result["reason"] = (
                    f"Homepage '{homepage_path}' requires startup file '{startup_path}', which "
                    f"imports package '{package}' without a browser import map. Ordinary static "
                    "hosting does not provide the module resolution this startup import needs."
                )
                return result

        # An uncertain declaration still blocks passing, but cannot hide a known rejection.
        if declaration_result is not None:
            return declaration_result
        return _check_static_resources(files, homepage_path, homepage_text, tree_sha)
    except UnicodeDecodeError:
        result["reason"] = "The repository file is not supported UTF-8 text; requirements remain pending."
        return result
    except requests.RequestException:
        result["dependency_status"] = "unavailable"
        result["reason"] = "Could not retrieve the fixed repository snapshot from GitHub. Try again."
        return result
    except (KeyError, TypeError, ValueError):
        result["dependency_status"] = "unavailable"
        result["reason"] = "GitHub returned malformed or incomplete snapshot data. Try again."
        return result


def _check_backend_declaration(owner, repo, files, tree_sha, budget):
    """Read an optional proposed MVP contract for team review, not a project requirement.

    A regular root git-gallery.json may declare initial_appearance_requires_backend
    and backend_runtime. True requires a runtime name. False or absence supplies no
    passing result. This checks declared requirements, not undeclared backend usage.
    """
    declaration_path = "git-gallery.json"
    if declaration_path not in files:
        return None
    result = {
        "dependency_status": "pending",
        "reason": "",
        "evidence_paths": [declaration_path],
        "tree_sha": tree_sha,
    }
    try:
        declaration_text = _read_snapshot_text(owner, repo, files[declaration_path], budget)
    except UnicodeDecodeError:
        result["reason"] = "git-gallery.json is not UTF-8 text; dependency checking remains pending."
        return result
    if declaration_text is None:
        result["reason"] = f"git-gallery.json could not be fully inspected: {budget['limit_reason']}"
        return result
    try:
        declaration = json.loads(declaration_text, object_pairs_hook=_unique_declaration_fields)
    except ValueError:
        result["reason"] = (
            "git-gallery.json contains malformed JSON or duplicate fields; "
            "dependency checking remains pending."
        )
        return result
    if not isinstance(declaration, dict):
        result["reason"] = "git-gallery.json must contain a JSON object; dependency checking remains pending."
        return result
    for field in declaration:
        if field not in ("initial_appearance_requires_backend", "backend_runtime"):
            result["reason"] = "git-gallery.json contains unrecognized fields; dependency checking remains pending."
            return result
    required = declaration.get("initial_appearance_requires_backend")
    if type(required) is not bool:
        result["reason"] = (
            "git-gallery.json must set initial_appearance_requires_backend to true or false; "
            "dependency checking remains pending."
        )
        return result
    runtime = declaration.get("backend_runtime")
    if "backend_runtime" in declaration:
        if not isinstance(runtime, str) or not runtime.strip() or not runtime.isprintable():
            result["reason"] = (
                "git-gallery.json must give backend_runtime as a nonblank, single-line name; "
                "dependency checking remains pending."
            )
            return result
        runtime = runtime.strip()
    if required is False:
        return None
    if runtime is None:
        result["reason"] = (
            "git-gallery.json declares a required initial backend but omits backend_runtime; "
            "dependency checking remains pending."
        )
        return result
    result["dependency_status"] = "rejected"
    result["reason"] = (
        f"git-gallery.json declares that {runtime} is required for the homepage's initial appearance. "
        "Application backends are unsupported."
    )
    return result


def _unique_declaration_fields(pairs):
    """Prevent duplicate JSON fields from silently replacing conflicting declarations."""
    fields = {}
    for name, value in pairs:
        if name in fields:
            raise ValueError("Duplicate declaration field.")
        fields[name] = value
    return fields


def _get_snapshot_files(owner: str, repo: str, tree_sha: str) -> dict:
    """Keep regular-file blob identities only after validating the complete listing."""
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}",
        headers=github_headers(),
        params={"recursive": "1"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if (
        not isinstance(data, dict)
        or data.get("truncated") is not False
        or data.get("sha") != tree_sha
        or not isinstance(data.get("tree"), list)
    ):
        raise ValueError("GitHub did not return a complete matching tree listing.")

    entry_types = {
        "100644": "blob", "100755": "blob", "040000": "tree",
        "120000": "blob", "160000": "commit",
    }
    files = {}
    seen_paths = set()
    for entry in data["tree"]:
        if not isinstance(entry, dict):
            raise ValueError("GitHub returned a malformed tree entry.")
        path = entry.get("path")
        mode = entry.get("mode")
        blob_sha = entry.get("sha")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or "\x00" in path
            or any(part in ("", ".", "..") for part in path.split("/"))
            or path in seen_paths
            or not isinstance(mode, str)
            or mode not in entry_types
            or entry.get("type") != entry_types[mode]
            or not isinstance(blob_sha, str)
            or re.fullmatch(r"[0-9a-f]{40}", blob_sha) is None
        ):
            raise ValueError("GitHub returned a malformed tree entry.")
        seen_paths.add(path)
        if mode in ("100644", "100755"):
            files[path] = blob_sha
    return files


def _read_snapshot_text(owner: str, repo: str, blob_sha: str, budget=None) -> str | None:
    """Preserve text decoding while sharing file retrieval with binary resources."""
    content = _read_snapshot_bytes(owner, repo, blob_sha, budget)
    if content is None:
        return None
    return content.decode("utf-8-sig")


def _read_snapshot_bytes(owner: str, repo: str, blob_sha: str, budget=None) -> bytes | None:
    """Validate a fixed blob; an optional inspection budget stops oversized reads."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{blob_sha}"
    headers = github_headers()
    if budget is None:
        # Existing callers retain the original request and validation behavior.
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    else:
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        try:
            response.raise_for_status()
            downloaded = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                budget["download_bytes"] += len(chunk)
                if budget["download_bytes"] > MAX_PROFILE_DOWNLOAD_BYTES:
                    budget["limit_reason"] = "The total file-download inspection limit was exceeded."
                    return None
                # Base64 and JSON need more space than the decoded file.
                if len(downloaded) + len(chunk) > MAX_PROFILE_FILE_BYTES * 2 + 4096:
                    budget["limit_reason"] = "The per-file download inspection limit was exceeded."
                    return None
                downloaded.extend(chunk)
            try:
                data = json.loads(downloaded)
            except UnicodeDecodeError:
                raise ValueError("GitHub returned malformed file JSON.") from None
        finally:
            response.close()
    if (
        not isinstance(data, dict)
        or data.get("sha") != blob_sha
        or data.get("encoding") != "base64"
        or not isinstance(data.get("content"), str)
        or type(data.get("size")) is not int
        or data["size"] < 0
    ):
        raise ValueError("GitHub returned malformed file information.")
    if budget is not None:
        if data["size"] > MAX_PROFILE_FILE_BYTES:
            budget["limit_reason"] = "The per-file inspection limit (2 MiB by default) was exceeded."
            return None
        if budget["content_bytes"] + data["size"] > MAX_PROFILE_CONTENT_BYTES:
            budget["limit_reason"] = "The total decoded file-content inspection limit was exceeded."
            return None
    try:
        # GitHub wraps Base64 content with newlines.
        content = base64.b64decode(data["content"].replace("\n", ""), validate=True)
    except binascii.Error:
        raise ValueError("GitHub returned malformed file encoding.") from None
    if len(content) != data["size"]:
        raise ValueError("GitHub returned incomplete file content.")
    if budget is not None:
        budget["content_bytes"] += len(content)
    return content


def _find_unresolved_startup_import(startup_text: str) -> str | None:
    """Recognize simple first-line imports; leave unfamiliar JavaScript undecided."""
    if "\x00" in startup_text:
        return None
    startup_text = startup_text.lstrip(" \t\r\n\f\v\ufeff")
    if not startup_text:
        return None
    first_line = startup_text.split("\n", 1)[0].rstrip("\r")
    match = re.fullmatch(
        r"import[ \t]+(.+?)[ \t]+from[ \t]+(['\"])([A-Za-z0-9_@$/.-]+)\2[ \t]*;?[ \t]*",
        first_line,
    )
    if match is None:
        return None
    bindings = match.group(1)
    identifier = r"[A-Za-z_$][A-Za-z0-9_$]*"
    binding_names = [bindings]
    if re.fullmatch(identifier, bindings) is None:
        if not bindings.startswith("{") or not bindings.endswith("}"):
            return None
        binding_names = []
        for name in bindings[1:-1].split(","):
            name = name.strip()
            if re.fullmatch(identifier, name) is None:
                return None
            binding_names.append(name)
    # Invalid binding words must not turn a syntax error into a dependency finding.
    reserved_bindings = {
        "await", "break", "case", "catch", "class", "const", "continue", "debugger",
        "default", "delete", "do", "else", "enum", "export", "extends", "false",
        "finally", "for", "function", "if", "implements", "import", "in", "instanceof",
        "interface", "let", "new", "null", "package", "private", "protected", "public",
        "return", "static", "super", "switch", "this", "throw", "true", "try", "typeof",
        "var", "void", "while", "with", "yield", "arguments", "eval",
    }
    for name in binding_names:
        if name in reserved_bindings:
            return None
    if len(set(binding_names)) != len(binding_names):
        return None
    package = match.group(3)
    if package.startswith((".", "/")):
        return None
    return package


def _resolve_resource_path(source_path: str, reference: str) -> str | None:
    """Return a repository path or external HTTP URL; uncertain references return None."""
    if not reference or reference != reference.strip() or "\\" in reference:
        return None
    if any(ord(character) < 32 for character in reference):
        return None
    try:
        parts = urlsplit(reference)
        if parts.scheme or parts.netloc:
            if parts.scheme not in ("", "http", "https") or not parts.hostname or parts.port == 0:
                return None
            if parts.username or parts.password or any(character.isspace() for character in reference):
                return None
            if not parts.scheme:
                return "https:" + reference
            return reference
        if not parts.path:
            return None
        if re.search(r"%(?![0-9A-Fa-f]{2})|%2[fF]|%5[cC]", parts.path):
            return None
        decoded_path = unquote(parts.path, errors="strict")
    except (ValueError, UnicodeDecodeError):
        return None
    if "\x00" in decoded_path or "\\" in decoded_path:
        return None
    if decoded_path.startswith("/"):
        path = posixpath.normpath(decoded_path).lstrip("/")
    else:
        path = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), decoded_path))
    if path in ("", ".", "..") or path.startswith("../"):
        return None
    return path


def _check_static_resources(files, homepage_path, homepage_text, tree_sha):
    """Check direct local file presence; leave resource contents to the browser."""
    result = {
        "dependency_status": "pending", "reason": "",
        "evidence_paths": [homepage_path], "tree_sha": tree_sha,
    }
    homepage = _StaticHomepageParser()
    try:
        homepage.feed(homepage_text)
        homepage.close()
    except (AssertionError, ValueError):
        result["reason"] = "The homepage resource references could not be inspected reliably."
        return result

    inspected_paths = set()
    has_uncertain_reference = False
    # A base URL changes relative references; do not guess that those files are missing.
    if not homepage.has_base_url:
        for reference in homepage.resources:
            path = _resolve_resource_path(homepage_path, reference)
            if path is None:
                has_uncertain_reference = True
                continue
            if path.startswith(("http://", "https://")) or path in inspected_paths:
                continue
            if path not in files:
                result["reason"] = f"Local resource '{path}' is missing or is not a regular file."
                return result
            inspected_paths.add(path)
            result["evidence_paths"].append(path)

    result["dependency_status"] = "passed"
    result["reason"] = (
        "The homepage meets the static-hosting prerequisite policy. Browser JavaScript "
        "and ordinary static resources are allowed; resource contents are not validated. "
        "JavaScript behavior, indirect resources, external availability and screenshot success "
        "remain unverified. Undeclared backend or build requirements may not be detected."
    )
    if homepage.has_base_url:
        result["reason"] += " Resource paths affected by an HTML base URL were not checked."
    elif has_uncertain_reference:
        result["reason"] += " Some resource references could not be resolved by this limited check."
    return result
