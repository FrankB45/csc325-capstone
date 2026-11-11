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
MAX_PROFILE_RESOURCES = 20
MAX_PROFILE_CONTENT_BYTES = 8 * 1024 * 1024
MAX_PROFILE_DOWNLOAD_BYTES = 16 * 1024 * 1024


class _StaticHomepageParser(HTMLParser):
    """Recognize passive native markup; unknown or executable features stay pending."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.is_supported = True
        self.open_tags = []
        self.seen_sections = set()
        self.has_content = False
        self.resources = []
        self.styles = []
        self.style_text = ""

    def handle_starttag(self, tag, attributes):
        containers = {
            "body", "main", "header", "footer", "nav", "section", "article", "div",
            "span", "h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li",
            "a", "strong", "em", "b", "i", "form", "label", "button", "textarea",
            "select", "option",
        }
        void_tags = {"meta", "link", "img", "input", "br", "hr"}
        allowed_attributes = {
            "id", "class", "title", "lang", "dir", "style", "role", "aria-label",
            "aria-labelledby", "aria-describedby", "href", "target", "rel", "type",
            "name", "value", "placeholder", "for", "rows", "cols", "action", "method",
            "src", "alt", "width", "height", "loading", "decoding", "charset", "content",
            "media", "as", "checked", "disabled", "required", "multiple", "selected",
        }
        values = {}
        for name, value in attributes:
            if name in values or name not in allowed_attributes or name.startswith("on"):
                self.is_supported = False
            if value is None and name not in {"checked", "disabled", "required", "multiple", "selected"}:
                self.is_supported = False
            if isinstance(value, str) and ("\x00" in value or "{{" in value or "{%" in value):
                self.is_supported = False
            if name in {"href", "action", "src"} and isinstance(value, str):
                if any(ord(character) < 32 for character in value) or value.strip().lower().startswith("javascript:"):
                    self.is_supported = False
            values[name] = value
        if not self.is_supported:
            return
        parent = None
        if self.open_tags:
            parent = self.open_tags[-1]

        if tag in {"html", "head", "body"}:
            if tag in self.seen_sections:
                self.is_supported = False
            if tag == "html" and parent is not None:
                self.is_supported = False
            if tag == "head" and (parent != "html" or "body" in self.seen_sections):
                self.is_supported = False
            if tag == "body" and (parent != "html" or "head" not in self.seen_sections):
                self.is_supported = False
            self.seen_sections.add(tag)
        elif tag in {"title", "meta", "link", "style"}:
            if parent != "head":
                self.is_supported = False
        elif tag not in containers and tag not in void_tags:
            self.is_supported = False
        elif "body" not in self.open_tags:
            self.is_supported = False

        if tag == "meta":
            if "charset" in values and values["charset"].lower() not in {"utf8", "utf-8"}:
                self.is_supported = False
        elif tag == "link":
            relation = values.get("rel", "").lower()
            if relation == "stylesheet" and values.get("type", "text/css").lower() == "text/css":
                self.resources.append(("stylesheet", values.get("href", "")))
            elif relation == "icon":
                self.resources.append(("image", values.get("href", "")))
            elif relation == "preload" and values.get("as") == "font":
                self.resources.append(("font", values.get("href", "")))
            else:
                self.is_supported = False
        elif tag == "img":
            self.resources.append(("image", values.get("src", "")))
            self.has_content = True
        elif tag == "input" and values.get("type", "text").lower() == "image":
            self.is_supported = False
        elif tag == "style":
            if values.get("type", "text/css").lower() != "text/css":
                self.is_supported = False
            self.style_text = ""
        if "style" in values:
            self.styles.append((values["style"], True))
        if tag not in void_tags:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if not self.open_tags or self.open_tags[-1] != tag:
            self.is_supported = False
            return
        if tag == "style":
            self.styles.append((self.style_text, False))
        self.open_tags.pop()

    def handle_startendtag(self, tag, attributes):
        if tag not in {"meta", "link", "img", "input", "br", "hr"}:
            self.is_supported = False
            return
        self.handle_starttag(tag, attributes)

    def handle_data(self, data):
        if "\x00" in data or any(marker in data for marker in ("{{", "{%", "<?", "<%")):
            self.is_supported = False
        if self.open_tags[-1:] == ["style"]:
            self.style_text += data
        elif data.strip() and "body" in self.open_tags:
            self.has_content = True
        elif data.strip() and self.open_tags[-1:] != ["title"]:
            self.is_supported = False

    def handle_decl(self, declaration):
        if declaration.lower() != "doctype html" or self.seen_sections:
            self.is_supported = False

    def handle_pi(self, data):
        self.is_supported = False

    def handle_comment(self, data):
        if data.lstrip().startswith(("#", "[if")):
            self.is_supported = False

    def unknown_decl(self, data):
        self.is_supported = False


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
    """Check the proposed declaration contract, passive profile and startup rule."""
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
        # An uncertain declaration blocks passing, but must not hide a known rejection.
        if declaration_result is None:
            profile_result = _check_static_homepage_profile(
                owner, repo, files, homepage_path, homepage_text, tree_sha, budget
            )
            if profile_result is not None:
                return profile_result
        homepage = _HomepageParser()
        try:
            homepage.feed(homepage_text)
            homepage.close()
        except (AssertionError, ValueError):
            result["reason"] = "The homepage markup could not be inspected reliably."
            return result

        required_tags = {"html", "head", "body", "div", "script"}
        if (
            not homepage.is_supported
            or homepage.open_tags
            or not required_tags.issubset(homepage.seen_tags)
            or not homepage.startup_source
        ):
            if declaration_result is not None:
                return declaration_result
            result["reason"] = (
                "The homepage has content, styling, scripts or markup outside the "
                "limited empty-page startup rule. Its dependency requirements remain pending."
            )
            return result

        source = homepage.startup_source
        try:
            source_url = urlsplit(source)
        except ValueError:
            result["reason"] = "The startup URL cannot be interpreted reliably."
            return result
        if (
            source_url.scheme
            or source_url.netloc
            or source_url.query
            or source_url.fragment
            or "\\" in source
            or "%" in source
            or any(ord(character) < 32 or character.isspace() for character in source)
        ):
            result["reason"] = "The startup URL is outside the local paths this check understands."
            return result
        startup_path = source_url.path
        if startup_path.startswith("./"):
            startup_path = startup_path[2:]
        elif startup_path.startswith("/"):
            startup_path = startup_path[1:]
        if not startup_path or any(part in ("", ".", "..") for part in startup_path.split("/")):
            result["reason"] = "The startup path cannot be resolved reliably by this limited check."
            return result
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
        if package is None:
            if declaration_result is not None:
                return declaration_result
            result["reason"] = (
                "The startup file does not begin with a recognized bare-package import. "
                "Other dependency requirements have not been ruled out."
            )
            return result

        result["dependency_status"] = "rejected"
        result["reason"] = (
            f"Homepage '{homepage_path}' requires startup file '{startup_path}', which "
            f"imports package '{package}' without a browser import map. Ordinary static "
            "hosting does not provide the module resolution this startup import needs."
        )
        return result
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
        if parts.query or parts.fragment or not parts.path:
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


def _inspect_stylesheet(css_text: str, declarations_only=False) -> list[str] | None:
    """Recognize flat CSS declarations and image URLs, not arbitrary CSS syntax."""
    references = []
    cleaned = []
    index = 0
    brace_depth = 0
    in_value = False
    while index < len(css_text):
        character = css_text[index]
        if css_text.startswith("/*", index):
            end = css_text.find("*/", index + 2)
            if end == -1:
                return None
            cleaned.append(" ")
            index = end + 2
        elif css_text[index:index + 4].lower() == "url(":
            if not in_value or (index > 0 and (css_text[index - 1].isalnum() or css_text[index - 1] in "_-")):
                return None
            start = index + 4
            while start < len(css_text) and css_text[start].isspace():
                start += 1
            if start >= len(css_text):
                return None
            if css_text[start] in ("'", '"'):
                quote = css_text[start]
                end = css_text.find(quote, start + 1)
                if end == -1:
                    return None
                reference = css_text[start + 1:end]
                closing = end + 1
                while closing < len(css_text) and css_text[closing].isspace():
                    closing += 1
                if closing >= len(css_text) or css_text[closing] != ")":
                    return None
            else:
                closing = css_text.find(")", start)
                if closing == -1:
                    return None
                reference = css_text[start:closing].strip()
                if any(character.isspace() or character in "('\\\"" for character in reference):
                    return None
            if not reference or "\\" in reference:
                return None
            references.append(reference)
            cleaned.append("resource")
            index = closing + 1
        elif character in ("'", '"'):
            if not in_value:
                return None
            end = css_text.find(character, index + 1)
            if end == -1 or "\\" in css_text[index + 1:end] or "\n" in css_text[index + 1:end]:
                return None
            cleaned.append("literal")
            index = end + 1
        elif character in "@$\\()\x00":
            # Imports, preprocessing and unfamiliar functions are outside this profile.
            return None
        else:
            if character == "{":
                brace_depth += 1
                in_value = False
            elif character == "}":
                brace_depth -= 1
                in_value = False
            elif character == ";":
                in_value = False
            elif character == ":" and (declarations_only or brace_depth == 1):
                in_value = True
            cleaned.append(character)
            index += 1

    text = "".join(cleaned).strip()
    blocks = []
    if declarations_only:
        if "{" in text or "}" in text:
            return None
        blocks.append(text)
    else:
        position = 0
        while position < len(text):
            opening = text.find("{", position)
            closing = text.find("}", position)
            if opening == -1 or closing < opening:
                return None
            selector = text[position:opening].strip()
            if re.fullmatch(r"[A-Za-z0-9_.*#,:>+~\s-]+", selector) is None:
                return None
            block = text[opening + 1:closing]
            if "{" in block:
                return None
            blocks.append(block)
            position = closing + 1
            while position < len(text) and text[position].isspace():
                position += 1
    for block in blocks:
        for declaration in block.split(";"):
            if not declaration.strip():
                continue
            name, separator, value = declaration.partition(":")
            if not separator or re.fullmatch(r"(?:--)?[A-Za-z][A-Za-z0-9-]*", name.strip()) is None:
                return None
            if re.fullmatch(r"[A-Za-z0-9_#.,% !/+\s-]+", value.strip()) is None:
                return None
    return references


def _check_image_signature(content: bytes) -> bool:
    """Identify common raster headers, without claiming complete image decoding."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return (
            len(content) >= 45 and content[8:16] == b"\x00\x00\x00\rIHDR"
            and int.from_bytes(content[16:20], "big") > 0
            and int.from_bytes(content[20:24], "big") > 0
            and content[-8:-4] == b"IEND"
        )
    if content.startswith(b"\xff\xd8"):
        return len(content) >= 12 and content.endswith(b"\xff\xd9")
    if content.startswith((b"GIF87a", b"GIF89a")):
        return (
            len(content) >= 14 and int.from_bytes(content[6:8], "little") > 0
            and int.from_bytes(content[8:10], "little") > 0 and content.endswith(b";")
        )
    if content.startswith(b"RIFF"):
        return (
            len(content) >= 20 and content[8:12] == b"WEBP"
            and int.from_bytes(content[4:8], "little") + 8 == len(content)
            and content[12:16] in (b"VP8 ", b"VP8L", b"VP8X")
        )
    return False


def _check_static_homepage_profile(owner, repo, files, homepage_path, homepage_text, tree_sha, budget):
    """Return a profile decision, or None so the original rejection rule can run."""
    homepage = _StaticHomepageParser()
    try:
        homepage.feed(homepage_text)
        homepage.close()
    except (AssertionError, ValueError):
        return None
    if (
        not homepage.is_supported or homepage.open_tags or not homepage.has_content
        or homepage.seen_sections != {"html", "head", "body"}
    ):
        return None
    result = {
        "dependency_status": "pending", "reason": "",
        "evidence_paths": [homepage_path], "tree_sha": tree_sha,
    }
    resources = []
    for kind, reference in homepage.resources:
        resources.append((kind, reference, homepage_path))
    for css_text, declarations_only in homepage.styles:
        references = _inspect_stylesheet(css_text, declarations_only)
        if references is None:
            result["reason"] = "Inline CSS is outside the bounded passive profile."
            return result
        for reference in references:
            resources.append(("image", reference, homepage_path))

    inspected = {}
    index = 0
    while index < len(resources):
        kind, reference, source_path = resources[index]
        index += 1
        path = _resolve_resource_path(source_path, reference)
        if path is None:
            result["reason"] = f"Resource reference '{reference}' in '{source_path}' is uncertain."
            return result
        if path.startswith(("http://", "https://")):
            continue
        if path in inspected:
            if inspected[path] != kind:
                result["reason"] = f"Resource '{path}' is used in conflicting contexts."
                return result
            continue
        if len(inspected) >= MAX_PROFILE_RESOURCES:
            result["reason"] = "The local-resource inspection limit (20 by default) was exceeded."
            return result
        if path not in files:
            result["reason"] = f"Local resource '{path}' is missing or is not a regular file."
            return result
        inspected[path] = kind
        result["evidence_paths"].append(path)
        content = _read_snapshot_bytes(owner, repo, files[path], budget)
        if content is None:
            result["reason"] = budget["limit_reason"]
            return result
        if kind == "stylesheet":
            references = _inspect_stylesheet(content.decode("utf-8-sig"))
            if references is None:
                result["reason"] = f"Stylesheet '{path}' uses syntax outside the bounded passive profile."
                return result
            for reference in references:
                resources.append(("image", reference, path))
        elif kind != "image" or not _check_image_signature(content):
            result["reason"] = f"Resource '{path}' is not a recognized raster image in this profile."
            return result
    result["dependency_status"] = "passed"
    result["reason"] = (
        "The homepage conforms to the bounded passive HTML/CSS/raster-image profile. "
        "This does not prove correct appearance, complete image decoding or screenshot success. "
        "External resource availability and other eligibility requirements remain unverified."
    )
    return result
