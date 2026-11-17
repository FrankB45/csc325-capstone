import base64
import json
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

import requests
from django.urls import reverse
from rest_framework.test import APIClient

from .services.dependencies import (
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

    def make_declaration_responses(self, declaration_content, homepage=None, startup_text=None):
        """Reuse the fixed-snapshot fixture with declaration retrieval before the homepage."""
        if homepage is None:
            homepage = self.static_homepage
        resources = [("git-gallery.json", declaration_content)]
        if startup_text is not None:
            resources.append(("src/main.js", startup_text))
        responses = self.make_static_responses(homepage, resources)
        declaration_response = responses.pop(4)
        responses.insert(3, declaration_response)
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

    def test_existing_page_content_and_optional_tooling_do_not_cause_rejection(self):
        self.homepage_text = self.homepage_text.replace(
            '<div id="root"></div>', '<h1>My portfolio</h1><div id="root"></div>'
        )
        for path in ("package.json", "vite.config.js", "server.py"):
            self.tree_data["tree"].append({
                "path": path, "mode": "100644", "type": "blob", "sha": "e" * 40,
            })

        result = self.check_dependencies()

        self.assertEqual(result["dependency_status"], "passed")
        self.assertIn("remain unverified", result["reason"])
        self.assertEqual(self.mock_get.call_count, 4)

    def test_committed_browser_javascript_passes_without_claiming_rendering_success(self):
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

                self.assertEqual(result["dependency_status"], "passed")
                self.assertIn("JavaScript behavior, indirect resources", result["reason"])
                self.assertIn("screenshot success remain unverified", result["reason"])
                self.assertEqual(result["evidence_paths"], ["index.html", "src/main.js"])
                self.assertEqual(self.mock_get.call_count, 5)
                self.assertNotIn("setup_available", result)

    def test_external_resources_do_not_cause_rejection_or_external_fetches(self):
        original_homepage = self.homepage_text
        homepages = (
            original_homepage.replace("./src/main.js", "https://cdn.example.com/start.js"),
            original_homepage.replace("</head>", '<link rel="stylesheet" href="https://cdn.example.com/site.css"></head>'),
            original_homepage.replace("</head>", '<link rel="preload" href="https://cdn.example.com/font.woff2" as="font"></head>'),
            original_homepage.replace('<div id="root"></div>', '<img src="https://cdn.example.com/logo.svg">'),
        )
        for homepage in homepages:
            with self.subTest(homepage=homepage):
                self.homepage_text = homepage

                result = self.check_dependencies()

                self.assertEqual(result["dependency_status"], "passed")
                self.assertEqual(self.mock_get.call_count, 4)
                for request in self.mock_get.call_args_list:
                    self.assertTrue(request.args[0].startswith("https://api.github.com/repos/"))

    def test_optional_backend_interaction_with_native_content_passes_profile(self):
        self.homepage_text = (
            '<html><head><title>Contact</title></head><body><h1>Contact me</h1>'
            '<form action="/api/contact" method="post" onsubmit="event.preventDefault(); fetch(this.action)">'
            '<input name="message">'
            '<button>Send</button></form></body></html>'
        )

        result = self.check_dependencies()

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(self.mock_get.call_count, 4)

    def test_alternative_browser_contexts_do_not_trigger_the_narrow_startup_rejection(self):
        original_homepage = self.homepage_text
        for path in ("site.css", "loader.js", "other.js"):
            self.tree_data["tree"].append({
                "path": path, "mode": "100644", "type": "blob", "sha": "e" * 40,
            })
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

                self.assertEqual(result["dependency_status"], "passed")
                self.assertIn("remain unverified", result["reason"])
                self.assertEqual(self.mock_get.call_count, 4)

    def test_unrecognized_startup_syntax_does_not_establish_rejection(self):
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

                self.assertEqual(result["dependency_status"], "passed")
                self.assertIn("JavaScript behavior", result["reason"])

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

    def test_browser_urls_and_uncertain_references_do_not_establish_rejection(self):
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

                self.assertEqual(result["dependency_status"], "passed")
                self.assertIn("remain unverified", result["reason"])
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

    def test_markup_outside_the_startup_rule_does_not_establish_rejection(self):
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

                self.assertEqual(result["dependency_status"], "passed")
                self.assertIn("remain unverified", result["reason"])
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

    def test_local_css_and_images_need_presence_not_custom_content_validation(self):
        homepage = self.static_homepage.replace(
            "</head>", '<link rel="stylesheet" href="/css/Site.css?v=1"></head>'
        ).replace("</body>", '<img src="./images/Logo.PNG#logo" alt="Logo"></body>')
        responses = self.make_static_responses(homepage, [
            ("css/Site.css", 'body { color: rgba(0, 0, 0, 0.5); width: calc(100% - 2px); }'),
            ("images/Logo.PNG", self.png_content),
        ], homepage_path="INDEX.HTML")

        result = self.check_dependencies(responses)

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(result["evidence_paths"], ["INDEX.HTML", "css/Site.css", "images/Logo.PNG"])
        self.assertEqual(result["tree_sha"], self.tree_sha)
        self.assertIn("static-hosting prerequisite policy", result["reason"])
        self.assertIn("resource contents are not validated", result["reason"])
        self.assertEqual(self.mock_get.call_count, 4)

    def test_inline_css_and_indirect_stylesheet_resources_are_not_interpreted(self):
        homepage = self.static_homepage.replace(
            "</head>", '<style>h1 { color: rgba(0,0,0,.5); }</style><link rel="stylesheet" href="css/theme.css"></head>'
        ).replace("<h1>", '<h1 style="width: calc(100% - 2px)">')
        stylesheet = '@font-face { src: url(font.woff2); } .hero { background: url(../images/Bg.svg); }'

        result = self.check_dependencies(self.make_static_responses(homepage, [("css/theme.css", stylesheet)]))

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(result["evidence_paths"], ["index.html", "css/theme.css"])
        self.assertIn("indirect resources", result["reason"])
        self.assertEqual(self.mock_get.call_count, 4)

    def test_passive_external_resources_are_allowed_without_external_requests(self):
        homepage = self.static_homepage.replace(
            "</head>", '<link rel="stylesheet" href="https://cdn.example.com/site.css">'
            '<link rel="preload" as="font" href="https://cdn.example.com/font.woff2"></head>'
        ).replace("</body>", '<img src="//cdn.example.com/logo.png" alt="Logo"></body>')

        result = self.check_dependencies(self.make_static_responses(homepage))

        self.assertEqual(result["dependency_status"], "passed")
        self.assertIn("external availability", result["reason"])
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

    def test_scripts_events_and_other_browser_features_are_allowed_without_execution(self):
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
                responses = self.make_static_responses(homepage, [("app.js", ""), ("other.html", "")])

                result = self.check_dependencies(responses)

                self.assertEqual(result["dependency_status"], "passed")
                self.assertIn("JavaScript behavior", result["reason"])
                self.assertEqual(self.mock_get.call_count, 4)

    def test_css_contents_do_not_determine_dependency_eligibility(self):
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
                self.assertEqual(result["dependency_status"], "passed")
                self.assertEqual(self.mock_get.call_count, 4)

    def test_missing_or_nonregular_direct_resources_remain_pending(self):
        resources = (
            '<img src="missing.svg">',
            '<script src="missing.js"></script>',
            '<link rel="stylesheet" href="missing.css">',
            '<link rel="preload" as="font" href="missing.woff2">',
        )
        for resource in resources:
            with self.subTest(resource=resource):
                homepage = self.static_homepage.replace("</body>", resource + "</body>")
                result = self.check_dependencies(self.make_static_responses(homepage))
                self.assertEqual(result["dependency_status"], "pending")
                self.assertIn("missing or is not a regular file", result["reason"])
                self.assertEqual(self.mock_get.call_count, 4)
        homepage = self.static_homepage.replace("</body>", '<img src="logo.svg"></body>')
        for mode, entry_type in (("120000", "blob"), ("040000", "tree"), ("160000", "commit")):
            with self.subTest(mode=mode):
                responses = self.make_static_responses(homepage, [("logo.svg", "<svg/>")])
                listing = responses[2].json()
                listing["tree"][-1]["mode"] = mode
                listing["tree"][-1]["type"] = entry_type
                responses[2] = self.make_response(listing)
                result = self.check_dependencies(responses)
                self.assertEqual(result["dependency_status"], "pending")
                self.assertEqual(self.mock_get.call_count, 4)

    def test_duplicate_resources_are_checked_once_without_guessing_content_types(self):
        homepage = self.static_homepage.replace("</body>", '<img src="logo.png"><img src="logo.png"></body>')
        homepage = homepage.replace("</head>", '<link rel="stylesheet" href="logo.png"></head>')

        result = self.check_dependencies(self.make_static_responses(homepage, [("logo.png", b"not decoded")]))

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(result["evidence_paths"], ["index.html", "logo.png"])
        self.assertEqual(self.mock_get.call_count, 4)

    def test_svg_fonts_and_other_committed_resource_formats_are_not_decoded(self):
        homepage = self.static_homepage.replace(
            "</head>", '<link rel="preload" as="font" href="font.woff2"></head>'
        ).replace("</body>", '<svg><text>Hello</text></svg><img src="logo.svg"><img src="photo.avif"></body>')
        responses = self.make_static_responses(homepage, [
            ("font.woff2", b"not decoded"), ("logo.svg", "<svg/>"), ("photo.avif", b"not decoded"),
        ])

        result = self.check_dependencies(responses)

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(result["evidence_paths"], ["index.html", "font.woff2", "logo.svg", "photo.avif"])
        self.assertIn("resource contents are not validated", result["reason"])
        self.assertEqual(self.mock_get.call_count, 4)

    def test_required_file_size_limits_return_pending(self):
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_FILE_BYTES", 8):
            result = self.check_dependencies(self.make_static_responses(self.static_homepage))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("per-file inspection limit", result["reason"])
        self.startup_text += "\n" + " " * 1000
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_FILE_BYTES", len(self.homepage_text.encode("utf-8")) + 1):
            result = self.check_dependencies()
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("per-file inspection limit", result["reason"])
        # Stylesheets are no longer downloaded, so their size does not consume this budget.
        homepage = self.static_homepage.replace("</head>", '<link rel="stylesheet" href="site.css"></head>')
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_FILE_BYTES", 512):
            result = self.check_dependencies(self.make_static_responses(homepage, [("site.css", " " * 600)]))
        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(self.mock_get.call_count, 4)

    def test_twenty_five_local_resources_with_duplicates_pass_without_extra_requests(self):
        resources = []
        resource_paths = []
        image_markup = ""
        for resource_number in range(25):
            resource_path = f"Images/Photo{resource_number:02d}.SVG"
            resources.append((resource_path, "<svg/>"))
            resource_paths.append(resource_path)
            image_markup += f'<img src="{resource_path}">'
        image_markup += '<img src="Images/Photo00.SVG"><img src="Images/Photo24.SVG">'
        homepage = self.static_homepage.replace("</body>", image_markup + "</body>")
        responses = self.make_static_responses(homepage, resources, homepage_path="INDEX.HTML")

        # Only metadata, revision, tree and homepage responses are available.
        result = self.check_dependencies(responses[:4])

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(result["evidence_paths"], ["INDEX.HTML"] + resource_paths)
        self.assertEqual(result["tree_sha"], self.tree_sha)
        self.assertEqual(self.mock_get.call_count, 4)

    def test_missing_twenty_first_local_resource_still_remains_pending(self):
        resources = []
        resource_paths = []
        image_markup = ""
        for resource_number in range(20):
            resource_path = f"Images/Photo{resource_number:02d}.SVG"
            resources.append((resource_path, "<svg/>"))
            resource_paths.append(resource_path)
            image_markup += f'<img src="{resource_path}">'
        image_markup += '<img src="Images/Missing21.SVG">'
        homepage = self.static_homepage.replace("</body>", image_markup + "</body>")
        responses = self.make_static_responses(homepage, resources)

        result = self.check_dependencies(responses[:4])

        self.assertEqual(result["dependency_status"], "pending")
        self.assertEqual(
            result["reason"],
            "Local resource 'Images/Missing21.SVG' is missing or is not a regular file.",
        )
        self.assertEqual(result["evidence_paths"], ["index.html"] + resource_paths)
        self.assertEqual(result["tree_sha"], self.tree_sha)
        self.assertEqual(self.mock_get.call_count, 4)

    def test_total_required_content_limit_returns_pending(self):
        limit = len(self.homepage_text.encode("utf-8")) + len(self.startup_text.encode("utf-8")) - 1
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_CONTENT_BYTES", limit):
            result = self.check_dependencies()
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

    def test_css_and_image_contents_are_not_downloaded(self):
        homepage = self.static_homepage.replace(
            "</head>", '<link rel="stylesheet" href="site.css"></head>'
        ).replace("</body>", '<img src="logo.png"></body>')
        responses = self.make_static_responses(homepage, [("site.css", ""), ("logo.png", b"")])
        responses[4] = AssertionError("Stylesheet contents must not be downloaded.")
        responses[5] = AssertionError("Image contents must not be downloaded.")

        result = self.check_dependencies(responses)

        self.assertEqual(result["dependency_status"], "passed")
        self.assertEqual(self.mock_get.call_count, 4)

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

    def test_declared_initial_backend_rejects_before_a_passive_profile_can_pass(self):
        for runtime in ("Node.js", "Python/Flask"):
            with self.subTest(runtime=runtime):
                declaration = json.dumps({
                    "initial_appearance_requires_backend": True,
                    "backend_runtime": runtime,
                })
                responses = self.make_declaration_responses(declaration)
                declaration_sha = responses[3].json()["sha"]

                result = self.check_dependencies(responses)

                self.assertEqual(result, {
                    "dependency_status": "rejected",
                    "reason": (
                        f"git-gallery.json declares that {runtime} is required for the homepage's initial appearance. "
                        "Application backends are unsupported."
                    ),
                    "evidence_paths": ["git-gallery.json"],
                    "tree_sha": self.tree_sha,
                })
                self.assertEqual(self.mock_get.call_count, 4)
                self.assertEqual(
                    self.mock_get.call_args.args[0],
                    f"https://api.github.com/repos/example/site/git/blobs/{declaration_sha}",
                )

    def test_false_declaration_keeps_optional_forms_and_external_resources_supported(self):
        homepage = (
            '<html><head><title>Contact</title>'
            '<link rel="stylesheet" href="https://cdn.example.com/site.css"></head>'
            '<body><h1>Contact me</h1><form action="/api/contact" method="post">'
            '<input name="message"><button>Send</button></form></body></html>'
        )
        declarations = (
            {"initial_appearance_requires_backend": False},
            {"initial_appearance_requires_backend": False, "backend_runtime": "Node.js"},
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                result = self.check_dependencies(
                    self.make_declaration_responses(json.dumps(declaration), homepage)
                )

                self.assertEqual(result["dependency_status"], "passed")
                self.assertIn("static-hosting prerequisite policy", result["reason"])
                self.assertEqual(result["evidence_paths"], ["index.html"])
                self.assertEqual(self.mock_get.call_count, 5)

    def test_false_declaration_does_not_bypass_the_browser_script_checks(self):
        declaration = json.dumps({"initial_appearance_requires_backend": False})
        responses = self.make_declaration_responses(
            declaration, self.homepage_text, 'document.getElementById("root").textContent = "Hello";'
        )

        result = self.check_dependencies(responses)

        self.assertEqual(result["dependency_status"], "passed")
        self.assertIn("JavaScript behavior", result["reason"])
        self.assertEqual(result["evidence_paths"], ["index.html", "src/main.js"])
        self.assertEqual(self.mock_get.call_count, 6)

        # False is not acceptance by itself: a definitely missing startup still stays pending.
        responses = self.make_declaration_responses(declaration, self.homepage_text)
        result = self.check_dependencies(responses)
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("missing or is not a regular file", result["reason"])

    def test_invalid_declarations_block_a_passive_profile_with_pending(self):
        declarations = (
            '{', '[]', '"a string"', '{}',
            '{"initial_appearance_requires_backend": true}',
            '{"initial_appearance_requires_backend": "true", "backend_runtime": "Node.js"}',
            '{"initial_appearance_requires_backend": 1, "backend_runtime": "Node.js"}',
            '{"initial_appearance_requires_backend": null}',
            '{"initial_appearance_requires_backend": true, "backend_runtime": ""}',
            '{"initial_appearance_requires_backend": true, "backend_runtime": "   "}',
            '{"initial_appearance_requires_backend": true, "backend_runtime": null}',
            '{"initial_appearance_requires_backend": false, "backend_runtime": 123}',
            '{"initial_appearance_requires_backend": false, "unknown_field": true}',
            '{"initial_appearance_requires_backend": false, "initial_appearance_requires_backend": true}',
            '{"initial_appearance_requires_backend": true, "backend_runtime": "Node.js", "backend_runtime": "Python"}',
            json.dumps({"initial_appearance_requires_backend": True, "backend_runtime": "Node\n.js"}),
            json.dumps({"initial_appearance_requires_backend": True, "backend_runtime": "\ud800"}),
            b'\xff',
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                result = self.check_dependencies(self.make_declaration_responses(declaration))

                self.assertEqual(result["dependency_status"], "pending")
                self.assertIn("git-gallery.json", result["reason"])
                self.assertIn("pending", result["reason"])
                self.assertEqual(result["evidence_paths"], ["git-gallery.json"])
                self.assertEqual(result["tree_sha"], self.tree_sha)

    def test_declaration_cannot_hide_the_existing_startup_import_rejection(self):
        declarations = (
            '{"initial_appearance_requires_backend": false}',
            '{',
            '{"initial_appearance_requires_backend": false, "initial_appearance_requires_backend": true}',
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                result = self.check_dependencies(self.make_declaration_responses(
                    declaration, self.homepage_text, self.startup_text
                ))

                self.assertEqual(result["dependency_status"], "rejected")
                self.assertIn("package 'react-dom/client'", result["reason"])
                self.assertIn("module resolution", result["reason"])
                self.assertEqual(result["evidence_paths"], ["index.html", "src/main.js"])
                self.assertEqual(self.mock_get.call_count, 6)

    def test_uncertain_declaration_is_retained_when_startup_evidence_is_ambiguous(self):
        responses = self.make_declaration_responses(
            '{}', self.homepage_text, 'document.getElementById("root").textContent = "Hello";'
        )

        result = self.check_dependencies(responses)

        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("git-gallery.json", result["reason"])
        self.assertEqual(result["evidence_paths"], ["git-gallery.json"])

    def test_undeclared_g_style_backend_usage_is_outside_this_limited_detection(self):
        # Source-shaped fixture from G at 6d0d57a4; its backend and script are never executed.
        homepage = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Forecast desk</title><link rel="icon" href="data:,">'
            '<link rel="stylesheet" href="styles.css"></head><body><main>'
            '<h1>Forecast desk.</h1><p>This page requires its Node backend to load the forecast.</p>'
            '<div id="forecast" role="status">Connecting to forecast service…</div>'
            '</main><script src="app.js"></script></body></html>'
        )
        responses = self.make_static_responses(homepage, [
            ("styles.css", ""), ("app.js", 'fetch("/api/forecast");'),
        ])

        result = self.check_dependencies(responses)

        self.assertEqual(result["dependency_status"], "passed")
        self.assertIn("Undeclared backend or build requirements may not be detected", result["reason"])
        self.assertEqual(result["evidence_paths"], ["index.html", "styles.css", "app.js"])
        self.assertEqual(self.mock_get.call_count, 4)

    def test_declaration_retrieval_failures_are_unavailable(self):
        failures = (
            self.make_response({}, 404), self.make_response({}, 403),
            requests.Timeout(), requests.ConnectionError(),
            self.make_response({}), self.make_response([]),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                responses = self.make_declaration_responses(
                    '{"initial_appearance_requires_backend": true, "backend_runtime": "Node.js"}'
                )
                responses[3] = failure

                result = self.check_dependencies(responses)

                self.assertEqual(result["dependency_status"], "unavailable")
                self.assertEqual(result["tree_sha"], self.tree_sha)
                self.assertEqual(self.mock_get.call_count, 4)

    def test_declaration_cannot_reject_from_an_incomplete_snapshot(self):
        for truncated in (True, None):
            with self.subTest(truncated=truncated):
                responses = self.make_declaration_responses(
                    '{"initial_appearance_requires_backend": true, "backend_runtime": "Node.js"}'
                )
                listing = responses[2].json()
                listing["truncated"] = truncated
                responses[2] = self.make_response(listing)

                result = self.check_dependencies(responses)

                self.assertEqual(result["dependency_status"], "unavailable")
                self.assertEqual(self.mock_get.call_count, 3)

    def test_declaration_reads_share_existing_inspection_limits(self):
        declaration = '{"initial_appearance_requires_backend": false}'
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_FILE_BYTES", 8):
            result = self.check_dependencies(self.make_declaration_responses(declaration))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("inspection limit", result["reason"])
        self.assertEqual(result["evidence_paths"], ["git-gallery.json"])
        self.assertEqual(self.mock_get.call_count, 4)

        content_limit = len(declaration.encode("utf-8")) + len(self.static_homepage.encode("utf-8")) - 1
        with patch("git_gallery_app.services.dependencies.MAX_PROFILE_CONTENT_BYTES", content_limit):
            result = self.check_dependencies(self.make_declaration_responses(declaration))
        self.assertEqual(result["dependency_status"], "pending")
        self.assertIn("total decoded file-content inspection limit", result["reason"])

    def test_declared_backend_rejection_reaches_the_real_compatibility_endpoint(self):
        declaration = '{"initial_appearance_requires_backend": true, "backend_runtime": "Node.js"}'
        self.mock_get.side_effect = self.make_declaration_responses(declaration)
        history_result = {"history_status": "passed", "reason": "Usable history.", "commit_count": 1}
        html_result = {"html_status": "passed", "reason": "Root homepage found.", "html_pages": ["index.html"]}
        with (
            patch("git_gallery_app.services.github.check_repository_history", return_value=history_result),
            patch("git_gallery_app.services.github.check_repository_html_pages", return_value=html_result),
            patch("git_gallery_app.services.analyses._get_collection", side_effect=AssertionError("No application storage access.")),
        ):
            response = APIClient().post(
                reverse("check-repository-compatibility"), {"url": self.repo_url}, format="json"
            )

        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["overall_status"], "rejected")
        self.assertIs(report["setup_available"], False)
        self.assertIs(report["same_snapshot_guaranteed"], False)
        self.assertEqual(report["history"], history_result)
        self.assertEqual(report["html"], html_result)
        self.assertEqual(report["dependencies"], {
            "status": "rejected",
            "reason": (
                "git-gallery.json declares that Node.js is required for the homepage's initial appearance. "
                "Application backends are unsupported."
            ),
            "evidence_paths": ["git-gallery.json"],
            "tree_sha": self.tree_sha,
        })
        self.assertEqual(self.mock_get.call_count, 4)

    def test_inspected_task_tracker_fixture_can_enter_setup_through_the_real_endpoint(self):
        # Based on Greenish-Eyes/my-first-repo at 1a7793497f3ec4e025cfc801462974226cff860a.
        # These committed files are only fixture text; the test never runs the website.
        homepage = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Task Tracker</title>
    <link rel="stylesheet" href="style.css" />
  </head>
  <body>
    <div class="container">
      <h1>Task Tracker</h1>
      <ul id="tasks">
        <li>Task 1</li>
        <li>Task 2</li>
        <li>Task 3</li>
      </ul>
    </div>

    <script src="script.js"></script>
  </body>
</html>
"""
        script = """/*
  This is just a sample project for my Git crash course. It doesn't do anything.
*/

console.log('Task Tracker Running...');
"""
        # Representative CSS from the same snapshot, including the formerly blocked rgba().
        stylesheet = """body {
  font-family: 'Roboto', sans-serif;
  background-color: #f4f4f4;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  width: 100%;
}
.container {
  width: 600px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 10px;
  background-color: #fff;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
"""
        dependency_responses = self.make_static_responses(homepage, [
            ("style.css", stylesheet), ("script.js", script),
        ])
        responses = [
            self.make_response(self.repository_data),
            self.make_response([{"sha": "1" * 40}, {"sha": "2" * 40}, {"sha": "3" * 40}]),
            self.make_response(self.repository_data),
            self.make_response(self.commit_data),
            self.make_response(dependency_responses[2].json()),
        ]
        responses.extend(dependency_responses)
        self.mock_get.side_effect = responses
        with patch(
            "git_gallery_app.services.analyses._get_collection",
            side_effect=AssertionError("No application storage access."),
        ):
            response = APIClient().post(
                reverse("check-repository-compatibility"), {"url": self.repo_url}, format="json"
            )

        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["overall_status"], "accepted")
        self.assertIs(report["setup_available"], True)
        self.assertIs(report["same_snapshot_guaranteed"], False)
        self.assertEqual(report["history"]["history_status"], "passed")
        self.assertEqual(report["history"]["commit_count"], 3)
        self.assertEqual(report["html"]["html_status"], "passed")
        self.assertEqual(report["html"]["html_pages"], ["index.html"])
        self.assertEqual(report["dependencies"]["status"], "passed")
        self.assertEqual(report["dependencies"]["tree_sha"], self.tree_sha)
        self.assertEqual(report["dependencies"]["evidence_paths"], ["index.html", "style.css", "script.js"])
        self.assertIn("JavaScript behavior, indirect resources", report["dependencies"]["reason"])
        self.assertIn("external availability and screenshot success remain unverified", report["dependencies"]["reason"])
        self.assertEqual(self.mock_get.call_count, 9)

    def test_base_urls_and_unresolved_references_are_qualified_without_false_missing_files(self):
        homepages = (
            self.static_homepage.replace("</head>", '<base href="https://cdn.example.com/site/"></head>')
                .replace("</body>", '<script src="app.js"></script></body>'),
            self.static_homepage.replace("</body>", '<img src="data:image/svg+xml,example"></body>'),
        )
        for homepage in homepages:
            with self.subTest(homepage=homepage):
                result = self.check_dependencies(self.make_static_responses(homepage))
                self.assertEqual(result["dependency_status"], "passed")
                self.assertEqual(result["evidence_paths"], ["index.html"])
                self.assertIn("remain unverified", result["reason"])
                self.assertEqual(self.mock_get.call_count, 4)
        self.assertIn("could not be resolved", result["reason"])

    def test_conflicting_resource_attributes_do_not_establish_a_missing_file(self):
        homepage = self.static_homepage.replace(
            "</body>", '<img src="logo.svg" src="missing.svg"></body>'
        )

        result = self.check_dependencies(self.make_static_responses(homepage, [("logo.svg", "<svg/>")]))

        self.assertEqual(result["dependency_status"], "passed")
        self.assertIn("could not be resolved", result["reason"])
        self.assertEqual(self.mock_get.call_count, 4)
