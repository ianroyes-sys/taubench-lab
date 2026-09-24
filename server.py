"""Local dashboard server. Runs only the free, scripted experiment."""

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
RUN_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("Host") not in {
            "127.0.0.1:%d" % self.server.server_port,
            "localhost:%d" % self.server.server_port,
        }:
            return self.respond(403, {"error": "Use the local dashboard address."})
        path = unquote(urlparse(self.path).path)
        if path in ("/api/results", "/api/upstream"):
            result = ROOT / (
                "results/latest.json"
                if path == "/api/results"
                else "results/upstream_reanalysis.json"
            )
            if not result.exists():
                return self.respond(
                    404, {"error": "No experiment yet. Run the scripted benchmark."}
                )
            return self.respond(200, result.read_bytes())
        if path.startswith("/api/"):
            return self.respond(404, {"error": "Unknown endpoint"})
        base = ROOT / ("docs" if path.startswith("/docs/") else "web")
        relative = path[6:] if path.startswith("/docs/") else path.lstrip("/")
        file = (base / (relative or "index.html")).resolve()
        if base not in file.parents or not file.is_file():
            return self.respond(404, {"error": "File not found"})
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        return self.respond(
            200,
            file.read_bytes(),
            mime + ("; charset=utf-8" if mime.startswith("text/") else ""),
        )

    def do_POST(self):
        if self.path != "/api/run":
            return self.respond(404, {"error": "Unknown endpoint"})
        host = self.headers.get("Host", "")
        allowed = {
            "127.0.0.1:%d" % self.server.server_port,
            "localhost:%d" % self.server.server_port,
        }
        origin = self.headers.get("Origin")
        if (
            host not in allowed
            or (origin and origin != "http://" + host)
            or self.headers.get("Sec-Fetch-Site") == "cross-site"
        ):
            return self.respond(
                403, {"error": "Run experiments from the local dashboard."}
            )
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.respond(400, {"error": "Invalid content length"})
        if size < 0 or size > 1024:
            return self.respond(413, {"error": "Request too large"})
        self.rfile.read(size)
        if not RUN_LOCK.acquire(blocking=False):
            return self.respond(409, {"error": "An experiment is already running."})
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "taulab",
                    "run",
                    "--output",
                    "results/latest.json",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode:
                return self.respond(
                    500,
                    {"error": "Experiment failed. Run the CLI to inspect the error."},
                )
            return self.respond(200, (ROOT / "results/latest.json").read_bytes())
        except subprocess.TimeoutExpired:
            return self.respond(
                504, {"error": "Experiment exceeded the local time limit."}
            )
        finally:
            RUN_LOCK.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("TauBench Lab: http://127.0.0.1:%s" % args.port, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
