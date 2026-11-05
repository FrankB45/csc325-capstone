import base64
import binascii
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

import requests

from .github import (
    _get_default_branch_tree_sha,
    get_repository_information,
    parse_github_url,
)


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


def check_repository_dependencies(repo_url: str) -> dict:
    """Check the approved startup-import rule without deciding full compatibility."""
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
        homepage_text = _read_snapshot_text(owner, repo, files[homepage_path])
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
        startup_text = _read_snapshot_text(owner, repo, files[startup_path])
        package = _find_unresolved_startup_import(startup_text)
        if package is None:
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


def _get_snapshot_files(owner: str, repo: str, tree_sha: str) -> dict:
    """Keep regular-file blob identities only after validating the complete listing."""
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}",
        headers={"Accept": "application/vnd.github+json"},
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


def _read_snapshot_text(owner: str, repo: str, blob_sha: str) -> str:
    """Read text by blob identity so a moving branch cannot change the inspected file."""
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{blob_sha}",
        headers={"Accept": "application/vnd.github+json"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if (
        not isinstance(data, dict)
        or data.get("sha") != blob_sha
        or data.get("encoding") != "base64"
        or not isinstance(data.get("content"), str)
        or type(data.get("size")) is not int
        or data["size"] < 0
    ):
        raise ValueError("GitHub returned malformed file information.")
    try:
        # GitHub wraps Base64 content with newlines.
        content = base64.b64decode(data["content"].replace("\n", ""), validate=True)
    except binascii.Error:
        raise ValueError("GitHub returned malformed file encoding.") from None
    if len(content) != data["size"]:
        raise ValueError("GitHub returned incomplete file content.")
    return content.decode("utf-8-sig")


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
