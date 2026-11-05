import base64
import json
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

import requests

from .services.dependencies import (
    _check_image_signature,
    _read_snapshot_bytes,
    _read_snapshot_text,
    check_repository_dependencies,
)


class RepositoryDependencyTests(TestCase):
    def setUp(self):
        self.repo_url = "https://github.com/example/site"
        self.tree_sha = "a" * 40
        self.homepage_sha = "b" * 40
        self.startup_sha = "c" * 40
        self.repository_data = {
            "name": "site",
            "full_name": "example/site",
            "description": "A static website",
            "default_branch": "main",
            "html_url": self.repo_url,
        }
        self.commit_data = {"commit": {"tree": {"sha": self.tree_sha}}}
        self.tree_data = {
            "sha": self.tree_sha,
            "truncated": False,
            "tree": [
                {"path": "index.html", "mode": "100644", "type": "blob", "sha": self.homepage_sha},
                {"path": "src", "mode": "040000", "type": "tree", "sha": "d" * 40},
                {"path": "src/main.js", "mode": "100644", "type": "blob", "sha": self.startup_sha},
            ],
        }
        self.homepage_text = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<title>Example</title></head><body><div id="root"></div>'
            '<script type="module" src="./src/main.js"></script></body></html>'
        )
        self.startup_text = (
            'import ReactDOM from "react-dom/client";\n'
            'ReactDOM.createRoot(document.getElementById("root")).render("Hello");'
        )
        self.static_homepage = '<html><head><title>Site</title></head><body><h1>Welcome</h1></body></html>'
        self.png_content = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jr1sAAAAASUVORK5CYII='
        )
        request_patch = patch("git_gallery_app.services.dependencies.requests.get")
        self.mock_get = request_patch.start()
        self.addCleanup(request_patch.stop)
        self.mock_get.side_effect = AssertionError("Unexpected GitHub request.")

    def make_response(self, data, status_code=200):
        response = requests.Response()
        response.status_code = status_code
        response.url = "https://api.github.com/repos/example/site"
        response._content = json.dumps(data).encode("utf-8")
        response._content_consumed = True
        return response

    def make_blob_response(self, content, blob_sha):
        if isinstance(content, str):
            content = content.encode("utf-8")
        return self.make_response({
            "sha": blob_sha,
            "encoding": "base64",
            "size": len(content),
            "content": base64.b64encode(content).decode("ascii") + "\n",
        })

    def make_responses(self):
        """Prepare the five requests shared by normal and failure scenarios."""
        return [
            self.make_response(self.repository_data),
            self.make_response(self.commit_data),
            self.make_response(self.tree_data),
            self.make_blob_response(self.homepage_text, self.homepage_sha),
            self.make_blob_response(self.startup_text, self.startup_sha),
        ]

    def check_dependencies(self, responses=None):
        self.mock_get.reset_mock()
        if responses is None:
            responses = self.make_responses()
        self.mock_get.side_effect = responses
        return check_repository_dependencies(self.repo_url)

    def make_static_responses(self, homepage, resources=(), homepage_path="index.html"):
        """Build a small fixed snapshot and its referenced file responses."""
        entries = [{
            "path": homepage_path, "mode": "100644", "type": "blob", "sha": self.homepage_sha,
        }]
        folders = set()
        resource_responses = []
        for number, (path, content) in enumerate(resources, start=16):
            parts = path.split("/")
            for depth in range(1, len(parts)):
                folder = "/".join(parts[:depth])
                if folder not in folders:
                    entries.append({"path": folder, "mode": "040000", "type": "tree", "sha": "d" * 40})
                    folders.add(folder)
            blob_sha = f"{number:040x}"
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob_sha})
            resource_responses.append(self.make_blob_response(content, blob_sha))
        responses = [
            self.make_response(self.repository_data),
            self.make_response(self.commit_data),
            self.make_response({"sha": self.tree_sha, "truncated": False, "tree": entries}),
            self.make_blob_response(homepage, self.homepage_sha),
        ]
        responses.extend(resource_responses)
        return responses

    def test_rejects_recognized_required_startup_imports_with_specific_evidence(self):
        imports = (
            ('import ReactDOM from "react-dom/client";', "react-dom/client"),
            ("import { createRoot } from 'react-dom/client';", "react-dom/client"),
            ('import { render, html } from "lit";', "lit"),
            ('import App from "@example/site-ui";', "@example/site-ui"),
        )
        for import_statement, package in imports:
            with self.subTest(import_statement=import_statement):
                self.startup_text = import_statement + '\nconsole.log("startup");'

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "rejected")
                self.assertEqual(result["evidence_paths"], ["index.html", "src/main.js"])
                self.assertEqual(result["tree_sha"], self.tree_sha)
                self.assertIn(f"package '{package}'", result["reason"])
                self.assertIn("index.html", result["reason"])
                self.assertIn("src/main.js", result["reason"])
                self.assertIn("module resolution", result["reason"])
                self.assertNotIn("build command", result["reason"])
                self.assertNotIn("backend", result["reason"])
                self.assertEqual(self.mock_get.call_count, 5)

    def test_uses_fixed_tree_and_blob_ids_and_preserves_filename_spelling(self):
        self.repository_data["default_branch"] = "release/site"
        self.tree_data["tree"][0]["path"] = "INDEX.HTML"
        self.tree_data["tree"][2]["path"] = "src/Start.JS"
        self.homepage_text = self.homepage_text.replace("./src/main.js", "/src/Start.JS")

        result = self.check_dependencies()

        self.assertEqual(result["dependency_status"], "rejected")
        self.assertEqual(result["evidence_paths"], ["INDEX.HTML", "src/Start.JS"])
        urls = []
        for request in self.mock_get.call_args_list:
            urls.append(request.args[0])
            self.assertEqual(request.kwargs["timeout"], 10)
        self.assertEqual(urls, [
            "https://api.github.com/repos/example/site",
            "https://api.github.com/repos/example/site/commits/heads%2Frelease%2Fsite",
            f"https://api.github.com/repos/example/site/git/trees/{self.tree_sha}",
            f"https://api.github.com/repos/example/site/git/blobs/{self.homepage_sha}",
            f"https://api.github.com/repos/example/site/git/blobs/{self.startup_sha}",
        ])
        self.assertEqual(self.mock_get.call_args_list[2].kwargs["params"], {"recursive": "1"})

    def test_existing_page_content_and_optional_tooling_remain_pending(self):
        self.homepage_text = self.homepage_text.replace(
            '<div id="root"></div>', '<h1>My portfolio</h1><div id="root"></div>'
        )
        for path in ("package.json", "vite.config.js", "server.py"):
            self.tree_data["tree"].append({
                "path": path, "mode": "100644", "type": "blob", "sha": "e" * 40,
            })

        result = self.check_dependencies()

        self.assertEqual(result["dependency_status"], "pending")
        self.assertEqual(self.mock_get.call_count, 4)

    def test_browser_ready_committed_entry_remains_pending_without_full_acceptance(self):
        self.tree_data["tree"].append({
            "path": "src/unused-source.jsx", "mode": "100644", "type": "blob", "sha": "e" * 40,
        })
        entries = (
            'document.getElementById("root").textContent = "Hello";',
            'import { render } from "./vendor/render.js";',
            'import ReactDOM from "https://esm.sh/react-dom/client";',
        )
        for entry in entries:
            with self.subTest(entry=entry):
                self.startup_text = entry

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")
                self.assertIn("not been ruled out", result["reason"])
                self.assertEqual(self.mock_get.call_count, 5)
                self.assertNotIn("setup_available", result)

    def test_external_resources_do_not_cause_rejection_or_external_fetches(self):
        original_homepage = self.homepage_text
        homepages = (
            original_homepage.replace("./src/main.js", "https://cdn.example.com/start.js"),
            original_homepage.replace("</head>", '<link rel="stylesheet" href="https://cdn.example.com/site.css"></head>'),
            original_homepage.replace("</head>", '<link rel="preload" href="https://cdn.example.com/font.woff2" as="font"></head>'),
            original_homepage.replace('<div id="root"></div>', '<img src="https://cdn.example.com/logo.png">'),
        )
        for homepage in homepages:
            with self.subTest(homepage=homepage):
                self.homepage_text = homepage

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")
                self.assertEqual(self.mock_get.call_count, 4)

    def test_optional_backend_interaction_with_native_content_passes_profile(self):
        self.homepage_text = (
            '<html><head><title>Contact</title></head><body><h1>Contact me</h1>'
            '<form action="/api/contact" method="post"><input name="message">'
            '<button>Send</button></form></body></html>'
        )

        result = self.check_dependencies()

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(self.mock_get.call_count, 4)

    def test_alternative_rendering_contexts_and_uncertain_markup_remain_pending(self):
        original_homepage = self.homepage_text
        homepages = (
            original_homepage.replace("</head>", '<base href="https://example.com/"></head>'),
            original_homepage.replace("</head>", '<style>body::before { content: "Hello"; }</style></head>'),
            original_homepage.replace("</head>", '<link rel="stylesheet" href="site.css"></head>'),
            original_homepage.replace("</head>", '<script type="importmap">{"imports":{"react-dom/client":"/vendor/react.js"}}</script></head>'),
            original_homepage.replace("</head>", '<script src="loader.js"></script></head>'),
            original_homepage.replace("</head>", '<script>window.startPage();</script></head>'),
            original_homepage.replace("<body>", '<body onload="startPage()">'),
            original_homepage.replace('<html lang="en">', '<html lang="en" onclick="startPage()">'),
            original_homepage.replace('<div id="root">', '<div id="root" onmouseover="startPage()">'),
            original_homepage.replace('type="module" src=', 'type="module" onload="startPage()" src='),
            original_homepage.replace("</body>", '<script type="module" src="other.js"></script></body>'),
            original_homepage.replace("</body>", '<noscript><h1>Fallback</h1></noscript></body>'),
            original_homepage.replace('<div id="root"></div>', '<div id="root" style="background: red"></div>'),
            original_homepage.replace("</head>", '<meta http-equiv="refresh" content="0;url=other.html"></head>'),
            original_homepage.replace('type="module" src=', 'type="module" async src='),
        )
        for homepage in homepages:
            with self.subTest(homepage=homepage):
                self.homepage_text = homepage

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")
                self.assertEqual(self.mock_get.call_count, 4)

    def test_unfamiliar_javascript_and_comment_or_string_matches_remain_pending(self):
        entries = (
            "", "not JavaScript", '/* import React from "react"; */',
            '// Optional tool\nimport React from "react";',
            '\'import React from "react";\';',
            'const optional = () => import("react");',
            'import * as React from "react";',
            'import { createRoot as mount } from "react-dom/client";',
            'import {\ncreateRoot\n} from "react-dom/client";',
            'import type React from "react";',
            'import React from "react"; // uncertain trailing syntax',
            'import React from "re\\u0061ct";',
            'import class from "react";',
            'import { default } from "react";',
            'import { createRoot, createRoot } from "react-dom/client";',
            '\x85import React from "react";',
            'import React from "react";\n\x00',
        )
        for entry in entries:
            with self.subTest(entry=entry):
                self.startup_text = entry

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")

    def test_missing_startup_is_pending_even_with_a_package_manifest(self):
        self.tree_data["tree"].pop()
        self.tree_data["tree"].append({
            "path": "package.json", "mode": "100644", "type": "blob", "sha": "e" * 40,
        })
        responses = self.make_responses()
        responses.append(self.make_blob_response(
            '{"scripts":{"build":"esbuild src/app.js --outfile=src/main.js"}}', "e" * 40
        ))

        result = self.check_dependencies(responses)

        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("missing or is not a regular file", result["reason"])
        self.assertEqual(self.mock_get.call_count, 4)

    def test_unsupported_startup_urls_remain_pending(self):
        original_homepage = self.homepage_text
        sources = (
            "//cdn.example.com/start.js", "data:text/javascript,alert(1)",
            "src/main.js?version=1", "src/main.js#version", "../main.js", "src//main.js",
            "src%2Fmain.js", "src\\main.js", " src/main.js", "\x00src/main.js", "//[", "",
        )
        for source in sources:
            with self.subTest(source=source):
                self.homepage_text = original_homepage.replace("./src/main.js", source)

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")
                self.assertEqual(self.mock_get.call_count, 4)

    def test_missing_or_ambiguous_homepage_remains_pending(self):
        original_entries = deepcopy(self.tree_data["tree"])
        entry_lists = (
            original_entries[1:],
            original_entries + [{
                "path": "INDEX.HTML", "mode": "100644", "type": "blob", "sha": "e" * 40,
            }],
        )
        for entries in entry_lists:
            with self.subTest(entries=entries):
                self.tree_data["tree"] = entries

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")
                self.assertEqual(self.mock_get.call_count, 3)

    def test_symlinks_directories_and_submodules_are_not_used_as_files(self):
        original_entries = deepcopy(self.tree_data["tree"])
        for entry_number in (0, 2):
            for mode, entry_type in (("120000", "blob"), ("040000", "tree"), ("160000", "commit")):
                with self.subTest(entry_number=entry_number, mode=mode):
                    self.tree_data["tree"] = deepcopy(original_entries)
                    self.tree_data["tree"][entry_number]["mode"] = mode
                    self.tree_data["tree"][entry_number]["type"] = entry_type

                    result = self.check_dependencies()

                    self.assertEqual(result["dependency_status"], "pending")
                    self.assertLess(self.mock_get.call_count, 5)

    def test_executable_regular_files_can_establish_the_rule(self):
        self.tree_data["tree"][0]["mode"] = "100755"
        self.tree_data["tree"][2]["mode"] = "100755"

        result = self.check_dependencies()

        self.assertEqual(result["dependency_status"], "rejected")

    def test_truncated_or_malformed_tree_responses_are_unavailable(self):
        original_tree = deepcopy(self.tree_data)
        payloads = (
            None, [], {},
            {**original_tree, "truncated": True},
            {**original_tree, "truncated": "false"},
            {**original_tree, "truncated": 0},
            {"sha": self.tree_sha, "tree": original_tree["tree"]},
            {**original_tree, "sha": "e" * 40},
            {**original_tree, "tree": {}},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                self.tree_data = payload

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "unavailable")
                self.assertEqual(self.mock_get.call_count, 3)

    def test_malformed_entries_prevent_rejection_from_partial_data(self):
        original_entries = deepcopy(self.tree_data["tree"])
        invalid_entries = (
            None, {},
            {"path": "bad.js", "mode": "100644", "type": "blob"},
            {"path": "../bad.js", "mode": "100644", "type": "blob", "sha": "e" * 40},
            {"path": "bad.js", "mode": "100644", "type": "tree", "sha": "e" * 40},
            {"path": "bad.js", "mode": [], "type": "blob", "sha": "e" * 40},
            {"path": "bad.js", "mode": "100644", "type": "blob", "sha": "not-a-sha"},
            original_entries[0],
        )
        for entry in invalid_entries:
            with self.subTest(entry=entry):
                self.tree_data["tree"] = original_entries + [entry]

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "unavailable")
                self.assertEqual(self.mock_get.call_count, 3)

    def test_malformed_metadata_and_commit_responses_are_unavailable(self):
        payloads = (None, [], {}, {"default_branch": 123})
        for request_number in (0, 1):
            for payload in payloads:
                with self.subTest(request_number=request_number, payload=payload):
                    responses = self.make_responses()
                    responses[request_number] = self.make_response(payload)

                    result = self.check_dependencies(responses)

                    self.assertEqual(result["dependency_status"], "unavailable")

    def test_malformed_blob_responses_are_unavailable(self):
        for request_number in (3, 4):
            valid_blob = self.make_responses()[request_number].json()
            payloads = (
                None, [], {},
                {**valid_blob, "sha": "e" * 40},
                {**valid_blob, "encoding": "utf-8"},
                {**valid_blob, "content": None},
                {**valid_blob, "content": "%%%"},
                {**valid_blob, "size": True},
                {**valid_blob, "size": -1},
                {**valid_blob, "size": valid_blob["size"] + 1},
            )
            for payload in payloads:
                with self.subTest(request_number=request_number, payload=payload):
                    responses = self.make_responses()
                    responses[request_number] = self.make_response(payload)

                    result = self.check_dependencies(responses)

                    self.assertEqual(result["dependency_status"], "unavailable")

    def test_invalid_json_at_each_request_is_unavailable(self):
        for request_number in range(5):
            with self.subTest(request_number=request_number):
                responses = self.make_responses()
                responses[request_number]._content = b"not JSON"

                result = self.check_dependencies(responses)

                self.assertEqual(result["dependency_status"], "unavailable")

    def test_http_failures_at_each_request_are_unavailable(self):
        for request_number in range(5):
            for status_code in (403, 404, 429, 503):
                with self.subTest(request_number=request_number, status_code=status_code):
                    responses = self.make_responses()
                    responses[request_number] = self.make_response({}, status_code)

                    result = self.check_dependencies(responses)

                    self.assertEqual(result["dependency_status"], "unavailable")
                    self.assertIn("GitHub", result["reason"])

    def test_timeouts_and_connection_failures_at_each_request_are_unavailable(self):
        for request_number in range(5):
            for error in (requests.Timeout(), requests.ConnectionError()):
                with self.subTest(request_number=request_number, error=type(error).__name__):
                    responses = self.make_responses()
                    responses[request_number] = error

                    result = self.check_dependencies(responses)

                    self.assertEqual(result["dependency_status"], "unavailable")

    def test_non_utf8_repository_content_remains_pending(self):
        for request_number, blob_sha in ((3, self.homepage_sha), (4, self.startup_sha)):
            with self.subTest(request_number=request_number):
                responses = self.make_responses()
                responses[request_number] = self.make_blob_response(b"\xff\xfe", blob_sha)

                result = self.check_dependencies(responses)

                self.assertEqual(result["dependency_status"], "pending")
                self.assertIn("UTF-8", result["reason"])

    def test_malformed_or_unfamiliar_homepage_markup_remains_pending(self):
        original_homepage = self.homepage_text
        homepages = (
            "", "not HTML", original_homepage.replace("</body>", ""),
            original_homepage.replace("</div>", "</span>"),
            original_homepage.replace('id="root"', 'id="root" id="other"'),
            original_homepage.replace('charset="utf-8"', "charset"),
            original_homepage.replace('charset="utf-8"', 'charset="iso-8859-1"'),
            original_homepage.replace('<div id="root"></div>', '<div id="root"/>'),
            original_homepage.replace("</head>", '<?php require "page.php"; ?></head>'),
            original_homepage.replace('<div id="root"></div>', '<!-- <div id="root"></div> -->'),
        )
        for homepage in homepages:
            with self.subTest(homepage=homepage):
                self.homepage_text = homepage

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")
                self.assertEqual(self.mock_get.call_count, 4)

    def test_invalid_url_and_missing_branch_do_not_establish_dependency_rejection(self):
        for repo_url in (None, "", "https://example.com/owner/repo"):
            with self.subTest(repo_url=repo_url):
                self.repo_url = repo_url

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")
                self.mock_get.assert_not_called()
        self.repo_url = "https://github.com/example/site"
        for default_branch in (None, "", "   "):
            with self.subTest(default_branch=default_branch):
                self.repository_data["default_branch"] = default_branch

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "pending")
                self.assertEqual(self.mock_get.call_count, 1)

    def test_local_css_and_raster_image_pass_the_bounded_profile(self):
        homepage = self.static_homepage.replace(
            "</head>", '<link rel="stylesheet" href="/css/Site.css"></head>'
        ).replace("</body>", '<img src="./images/Logo.PNG" alt="Logo"></body>')
        responses = self.make_static_responses(homepage, [
            ("css/Site.css", 'body { color: #333; margin: 0; } .hero { padding: 8px; }'),
            ("images/Logo.PNG", self.png_content),
        ], homepage_path="INDEX.HTML")

        result = self.check_dependencies(responses)

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(result["evidence_paths"], ["INDEX.HTML", "css/Site.css", "images/Logo.PNG"])
        self.assertEqual(result["tree_sha"], self.tree_sha)
        self.assertIn("conforms", result["reason"])
        self.assertIn("does not prove", result["reason"])
        self.assertIn("screenshot success", result["reason"])
        self.assertEqual(self.mock_get.call_count, 6)

    def test_inline_css_and_stylesheet_relative_images_are_inspected(self):
        homepage = self.static_homepage.replace(
            "</head>", '<style>h1 { color: navy; }</style><link rel="stylesheet" href="css/theme.css"></head>'
        ).replace("<h1>", '<h1 style="margin: 0; padding: 4px">')
        stylesheet = (
            '/* url(missing-comment.png) */ .hero { background-image: url("../images/Bg.PNG"); } '
            'p::before { content: "url(missing-string.png)"; }'
        )

        result = self.check_dependencies(self.make_static_responses(homepage, [
            ("css/theme.css", stylesheet), ("images/Bg.PNG", self.png_content),
        ]))

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(result["evidence_paths"], ["index.html", "css/theme.css", "images/Bg.PNG"])
        self.assertEqual(self.mock_get.call_count, 6)

    def test_passive_external_resources_are_allowed_without_external_requests(self):
        homepage = self.static_homepage.replace(
            "</head>", '<link rel="stylesheet" href="https://cdn.example.com/site.css">'
            '<link rel="preload" as="font" href="https://cdn.example.com/font.woff2"></head>'
        ).replace("</body>", '<img src="//cdn.example.com/logo.png" alt="Logo"></body>')

        result = self.check_dependencies(self.make_static_responses(homepage))

        self.assertEqual(result["dependency_status"], "passed")
        self.assertIn("External resource availability", result["reason"])
        self.assertEqual(self.mock_get.call_count, 4)
        for request in self.mock_get.call_args_list:
            self.assertTrue(request.args[0].startswith("https://api.github.com/repos/"))

    def test_generated_static_content_ignores_unused_tools_and_server_files(self):
        result = self.check_dependencies(self.make_static_responses(self.static_homepage, [
            ("package.json", '{"scripts":{"build":"some-build-tool"}}'),
            ("src/unused.jsx", 'import App from "app-package";'),
            ("server.py", 'raise RuntimeError("Never execute this fixture")'),
        ]))

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(self.mock_get.call_count, 4)

    def test_visible_content_does_not_make_javascript_optional(self):
        homepages = (
            self.static_homepage.replace("</head>", '<script src="app.js"></script></head>'),
            self.static_homepage.replace("</head>", '<script src="https://cdn.example.com/app.js"></script></head>'),
            self.static_homepage.replace("</head>", '<script>document.body.replaceChildren();</script></head>'),
            self.static_homepage.replace("<h1>", '<h1 onclick="changePage()">'),
            self.static_homepage.replace("</body>", '<iframe src="other.html"></iframe></body>'),
            self.static_homepage.replace("</head>", '<base href="/elsewhere/"></head>'),
            self.static_homepage.replace("Welcome", "{{ page_content }}"),
            self.static_homepage.replace("</body>", '<!--#include virtual="header.html" --></body>'),
            self.static_homepage.replace("Welcome", '<a href="java&#9;script:changePage()">Welcome</a>'),
        )
        for homepage in homepages:
            with self.subTest(homepage=homepage):
                result = self.check_dependencies(self.make_static_responses(homepage))
                self.assertEqual(result["dependency_status"], "pending")
                self.assertEqual(self.mock_get.call_count, 4)

    def test_unrecognized_css_or_uncertain_css_urls_remain_pending(self):
        homepage = self.static_homepage.replace("</head>", '<link rel="stylesheet" href="css/site.css"></head>')
        stylesheets = (
            '@import "theme.css";', '.a { .b { color: red; } }', '$color: red;',
            'p { color: var(--color); }', 'p { width: calc(100% - 2px); }',
            'p { broken declaration }', 'p { color: red;', '/* unfinished',
            'p { content: "unfinished; }', 'p { background: url("escaped\\name.png"); }',
            'p { background: url(data:image/png;base64,AAAA); }',
            'p { background: url(../../outside.png); }',
            'p { background: noturl(logo.png); }', 'url(logo.png) { color: red; }',
            'p { "color": red; }',
        )
        for stylesheet in stylesheets:
            with self.subTest(stylesheet=stylesheet):
                result = self.check_dependencies(self.make_static_responses(homepage, [("css/site.css", stylesheet)]))
                self.assertEqual(result["dependency_status"], "pending")

    def test_missing_nonregular_or_unrecognized_assets_remain_pending(self):
        homepage = self.static_homepage.replace("</body>", '<img src="logo.png" alt="Logo"></body>')
        result = self.check_dependencies(self.make_static_responses(homepage))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("missing or is not a regular file", result["reason"])
        for content in (b"not an image", b"\x89PNG\r\n\x1a\n", b"<svg></svg>"):
            with self.subTest(content=content):
                result = self.check_dependencies(self.make_static_responses(homepage, [("logo.png", content)]))
                self.assertEqual(result["dependency_status"], "pending")
                self.assertIn("not a recognized raster image", result["reason"])
        responses = self.make_static_responses(homepage, [("logo.png", self.png_content)])
        listing = responses[2].json()
        listing["tree"][-1]["mode"] = "120000"
        responses[2] = self.make_response(listing)
        result = self.check_dependencies(responses)
        self.assertEqual(result["dependency_status"], "pending")
        self.assertEqual(self.mock_get.call_count, 4)

    def test_duplicate_resources_are_read_once_and_conflicting_uses_stay_pending(self):
        homepage = self.static_homepage.replace("</body>", '<img src="logo.png"><img src="logo.png"></body>')
        result = self.check_dependencies(self.make_static_responses(homepage, [("logo.png", self.png_content)]))
        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(self.mock_get.call_count, 5)
        homepage = homepage.replace("</head>", '<link rel="stylesheet" href="logo.png"></head>')
        result = self.check_dependencies(self.make_static_responses(homepage, [("logo.png", 'p { color: red; }')]))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("conflicting contexts", result["reason"])

    def test_raster_signatures_identify_formats_without_decoding_images(self):
        # The three synthetic headers below test identification, not image decoding.
        signatures = (
            self.png_content,
            b"\xff\xd8" + b"header-data" + b"\xff\xd9",
            b"GIF89a\x01\x00\x01\x00\x00\x00\x00;",
            b"RIFF\x0c\x00\x00\x00WEBPVP8 \x00\x00\x00\x00",
        )
        for content in signatures:
            with self.subTest(content=content):
                self.assertTrue(_check_image_signature(content))
        for content in (b"", b"\xff\xd8\xff\xd9", b"GIF89a", b"RIFF", self.png_content[:-12]):
            with self.subTest(content=content):
                self.assertFalse(_check_image_signature(content))

    def test_file_size_limit_returns_pending(self):
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_FILE_BYTES", 8):
            result = self.check_dependencies(self.make_static_responses(self.static_homepage))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("per-file inspection limit", result["reason"])
        self.startup_text += "\n" + " " * 1000
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_FILE_BYTES", len(self.homepage_text.encode("utf-8")) + 1):
            result = self.check_dependencies()
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("per-file inspection limit", result["reason"])
        homepage = self.static_homepage.replace("</head>", '<link rel="stylesheet" href="site.css"></head>')
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_FILE_BYTES", 512):
            result = self.check_dependencies(self.make_static_responses(homepage, [("site.css", " " * 600)]))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("per-file inspection limit", result["reason"])

    def test_resource_count_limit_returns_pending(self):
        homepage = self.static_homepage.replace("</body>", '<img src="a.png"><img src="b.png"></body>')
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_RESOURCES", 1):
            result = self.check_dependencies(self.make_static_responses(homepage, [
                ("a.png", self.png_content), ("b.png", self.png_content),
            ]))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("local-resource inspection limit", result["reason"])
        self.assertEqual(self.mock_get.call_count, 5)

    def test_total_decoded_content_limit_returns_pending(self):
        homepage = self.static_homepage.replace("</body>", '<img src="logo.png"></body>')
        limit = len(homepage.encode("utf-8")) + len(self.png_content) - 1
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_CONTENT_BYTES", limit):
            result = self.check_dependencies(self.make_static_responses(homepage, [("logo.png", self.png_content)]))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("total decoded file-content inspection limit", result["reason"])

    def test_total_download_limit_returns_pending(self):
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_DOWNLOAD_BYTES", 100):
            result = self.check_dependencies(self.make_static_responses(self.static_homepage))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("total file-download inspection limit", result["reason"])

    def test_streaming_stops_and_closes_response_at_the_limit(self):
        response = self.make_response({})
        def chunks(chunk_size):
            yield b"x" * 5000
            self.fail("The reader continued after exceeding its inspection limit.")
        budget = {"content_bytes": 0, "download_bytes": 0, "limit_reason": ""}
        self.mock_get.side_effect = [response]
        with patch.object(response, "iter_content", side_effect=chunks):
            with patch.object(response, "close") as close_response:
                with patch("git_gallery_app.services.dependencies.MAX_PROFILE_FILE_BYTES", 8):
                    content = _read_snapshot_bytes("example", "site", self.homepage_sha, budget)
        self.assertIsNone(content)
        self.assertIn("per-file download inspection limit", budget["limit_reason"])
        close_response.assert_called_once_with()

    def test_shared_byte_reader_preserves_original_text_request_and_decoding(self):
        self.mock_get.side_effect = [self.make_blob_response("\ufeffHello, café", self.homepage_sha)]

        text = _read_snapshot_text("example", "site", self.homepage_sha)

        self.assertEqual(text, "Hello, café")
        self.mock_get.assert_called_once_with(
            f"https://api.github.com/repos/example/site/git/blobs/{self.homepage_sha}",
            headers={"Accept": "application/vnd.github+json"}, timeout=10,
        )

    def test_shared_byte_reader_preserves_validation_and_request_errors(self):
        original_blob = self.make_blob_response("Hello", self.homepage_sha).json()
        payloads = (
            {**original_blob, "sha": "e" * 40}, {**original_blob, "encoding": "utf8"},
            {**original_blob, "content": "%%%"}, {**original_blob, "size": 999},
            {**original_blob, "size": True},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                self.mock_get.side_effect = [self.make_response(payload)]
                with self.assertRaises(ValueError):
                    _read_snapshot_text("example", "site", self.homepage_sha)
        for error in (requests.Timeout(), requests.ConnectionError()):
            with self.subTest(error=type(error).__name__):
                self.mock_get.side_effect = error
                with self.assertRaises(type(error)):
                    _read_snapshot_text("example", "site", self.homepage_sha)
        self.mock_get.side_effect = [self.make_response({}, 404)]
        with self.assertRaises(requests.HTTPError):
            _read_snapshot_text("example", "site", self.homepage_sha)
        self.mock_get.side_effect = [self.make_blob_response(b"\xff", self.homepage_sha)]
        with self.assertRaises(UnicodeDecodeError):
            _read_snapshot_text("example", "site", self.homepage_sha)

    def test_new_resource_retrieval_failures_are_unavailable(self):
        homepage = self.static_homepage.replace(
            "</head>", '<link rel="stylesheet" href="site.css"></head>'
        ).replace("</body>", '<img src="logo.png"></body>')
        for request_number in (4, 5):
            for failure in (self.make_response({}, 404), requests.Timeout(), self.make_response({})):
                with self.subTest(request_number=request_number, failure=type(failure).__name__):
                    responses = self.make_static_responses(homepage, [
                        ("site.css", 'p { color: red; }'), ("logo.png", self.png_content),
                    ])
                    responses[request_number] = failure
                    result = self.check_dependencies(responses)
                    self.assertEqual(result["dependency_status"], "unavailable")

    def test_positive_profile_requires_a_complete_validated_snapshot(self):
        for truncated in (True, "false", None):
            with self.subTest(truncated=truncated):
                responses = self.make_static_responses(self.static_homepage)
                listing = responses[2].json()
                listing["truncated"] = truncated
                responses[2] = self.make_response(listing)
                result = self.check_dependencies(responses)
                self.assertEqual(result["dependency_status"], "unavailable")
                self.assertEqual(self.mock_get.call_count, 3)
