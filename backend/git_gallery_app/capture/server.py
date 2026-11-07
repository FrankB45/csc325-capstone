"""Serve a folder over HTTP so a browser can load it like a real website.

Runs inside the capture child process, so this module must NOT import Django.
"""
import functools
import http.server
import threading
from contextlib import contextmanager
from pathlib import Path


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Python's built-in file server, minus the log line it prints per request."""

    def log_message(self, format, *args):
        pass


@contextmanager
def serve_directory(root):
    """Serve `root` on a free local port. Yields the base URL, e.g. "http://127.0.0.1:54321".

    Usage:
        with serve_directory(folder) as base_url:
            ...  # the server is running here
        # the server is stopped here, even if an error happened inside the block
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"Cannot serve {root}: it is not a directory.")

    # The server creates a new handler object for every request, and only passes
    # it request details. partial() "pre-fills" directory= so each one knows what to serve.
    handler = functools.partial(_QuietHandler, directory=str(root))

    # 127.0.0.1 = reachable only from this machine. Port 0 = let the OS pick a free port.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)

    # serve_forever() never returns, so run it in a background thread.
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.1},
        daemon=True,
    )
    thread.start()

    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()       # stop the serve_forever() loop
        server.server_close()   # release the port
        thread.join()           # wait for the background thread to finish