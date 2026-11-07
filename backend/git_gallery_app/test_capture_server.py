import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from .capture.server import serve_directory   # use "..capture.server" if your tests are in tests/

# An opener with no proxy. If your computer or network has a proxy configured,
# urllib would otherwise try to send our localhost requests through it.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch(url):
    """GET a URL and return (status_code, body_text)."""
    with _opener.open(url, timeout=5) as response:
        return response.status, response.read().decode("utf-8")


class ServeDirectoryTests(unittest.TestCase):
    def setUp(self):
        # A throwaway folder that looks like a tiny website:
        #   <temp>/secret.txt          ← outside the site; must NOT be reachable
        #   <temp>/site/index.html
        #   <temp>/site/css/style.css
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)   # delete the folder after each test, pass or fail

        self.root = Path(temp.name) / "site"
        (self.root / "css").mkdir(parents=True)
        (self.root / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")
        (self.root / "css" / "style.css").write_text("h1 { color: red; }", encoding="utf-8")
        (Path(temp.name) / "secret.txt").write_text("do not serve", encoding="utf-8")

    def test_serves_a_file(self):
        with serve_directory(self.root) as base_url:
            self.assertEqual(fetch(f"{base_url}/index.html"), (200, "<h1>Hello</h1>"))

    def test_serves_root_relative_paths(self):
        # This is exactly what breaks under file:// and is the reason this piece exists.
        with serve_directory(self.root) as base_url:
            self.assertEqual(fetch(f"{base_url}/css/style.css"), (200, "h1 { color: red; }"))

    def test_missing_file_is_404(self):
        with serve_directory(self.root) as base_url:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                fetch(f"{base_url}/nope.html")
            self.assertEqual(caught.exception.code, 404)

    def test_cannot_escape_the_folder(self):
        # A malicious page could try "../" to read files outside the site.
        with serve_directory(self.root) as base_url:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                fetch(f"{base_url}/../secret.txt")
            self.assertEqual(caught.exception.code, 404)

    def test_two_servers_get_different_ports(self):
        with serve_directory(self.root) as first, serve_directory(self.root) as second:
            self.assertNotEqual(first, second)

    def test_server_stops_after_with_block(self):
        with serve_directory(self.root) as base_url:
            pass
        # Nothing is listening any more, so the connection itself fails.
        with self.assertRaises(urllib.error.URLError):
            fetch(f"{base_url}/index.html")

    def test_rejects_missing_folder(self):
        with self.assertRaises(FileNotFoundError):
            with serve_directory(self.root / "does-not-exist"):
                pass