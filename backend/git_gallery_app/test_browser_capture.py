import tempfile
import unittest
from pathlib import Path

from .capture.errors import CaptureError      # ".." versions if your tests are in tests/
from .capture.server import serve_directory

from .capture.browser import screenshot_page


def png_size(path):
    """Read (width, height) straight from a PNG file's header. No image library needed."""
    with open(path, "rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path} is not a PNG file")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height


class ScreenshotPageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.site = Path(temp.name) / "site"
        self.site.mkdir()
        self.out = Path(temp.name) / "shot.png"

    def write_page(self, path, html):
        file = self.site / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(html, encoding="utf-8")

    def capture(self, page_path="index.html", **options):
        """Serve self.site with Piece 2 and screenshot it with Piece 4."""
        options = {"width": 800, "height": 600, **options}
        with serve_directory(self.site) as base_url:
            return screenshot_page(base_url, page_path, self.out, **options)

    def test_saves_png_at_viewport_size(self):
        self.write_page("index.html", "<h1>Hello</h1>")
        self.capture(full_page=False)
        self.assertEqual(png_size(self.out), (800, 600))

    def test_full_page_includes_content_below_the_fold(self):
        self.write_page("index.html", '<body style="margin:0"><div style="height:2500px">tall</div></body>')
        self.capture(full_page=True)
        width, height = png_size(self.out)
        self.assertEqual(width, 800)              # width stays fixed (US: consistent viewport)
        self.assertGreaterEqual(height, 2500)     # height grows with the content

    def test_viewport_only_when_full_page_is_false(self):
        self.write_page("index.html", '<div style="height:2500px">tall</div>')
        self.capture(full_page=False)
        self.assertEqual(png_size(self.out), (800, 600))

    def test_pages_in_subfolders_and_names_with_spaces(self):
        self.write_page("about us/team.html", "<h1>Team</h1>")
        self.capture(page_path="about us/team.html")
        self.assertTrue(self.out.exists())

    def test_missing_page_raises_capture_error(self):
        self.write_page("index.html", "<h1>Hello</h1>")
        with self.assertRaises(CaptureError) as caught:
            self.capture(page_path="missing.html")
        self.assertIn("404", str(caught.exception))
        self.assertFalse(self.out.exists())       # no half-made screenshot left behind

    def test_blocks_requests_to_other_servers(self):
        self.write_page("index.html", """
            <link rel="stylesheet" href="https://cdn.example.com/theme.css">
            <img src="http://127.0.0.1:1/not-our-server.png">
            <h1>Still renders</h1>
        """)
        blocked = self.capture()
        self.assertIn("https://cdn.example.com/theme.css", blocked)
        # Same machine, different port: still blocked. This protects your Django API.
        self.assertIn("http://127.0.0.1:1/not-our-server.png", blocked)
        self.assertTrue(self.out.exists())        # blocking doesn't stop the screenshot

    def test_allows_the_sites_own_files(self):
        self.write_page("index.html", '<link rel="stylesheet" href="/css/site.css"><h1>Hi</h1>')
        self.write_page("css/site.css", "h1 { color: red; }")
        self.assertEqual(self.capture(), [])