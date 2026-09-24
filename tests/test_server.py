from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import importlib.util
import threading
import unittest

spec = importlib.util.spec_from_file_location(
    "dashboard_server", Path(__file__).resolve().parents[1] / "server.py"
)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def request(self, method, path, headers=None):
        conn = HTTPConnection("127.0.0.1", self.httpd.server_port)
        conn.request(method, path, headers=headers or {})
        response = conn.getresponse()
        body = response.read()
        status = response.status
        conn.close()
        return status, body

    def test_cannot_serve_source_or_traverse(self):
        for path in [
            "/../server.py",
            "/%2e%2e/server.py",
            "/docs/../server.py",
            "/.env",
        ]:
            self.assertEqual(self.request("GET", path)[0], 404)

    def test_cross_origin_run_blocked(self):
        self.assertEqual(
            self.request("POST", "/api/run", {"Origin": "https://evil.example"})[0], 403
        )

    def test_rebinding_host_run_blocked(self):
        self.assertEqual(
            self.request("POST", "/api/run", {"Host": "evil.example"})[0], 403
        )
        self.assertEqual(
            self.request("GET", "/api/results", {"Host": "evil.example"})[0], 403
        )

    def test_archived_results_available(self):
        status, body = self.request("GET", "/api/upstream")
        self.assertEqual(status, 200)
        self.assertIn(b"archived_reward_reanalysis", body)
