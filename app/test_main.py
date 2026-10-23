import http.client
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

import main

GOOD = {"patient_id": "p-1001", "provider_id": "dr-42", "slot": "2026-11-02T15:00:00Z"}


class AppointmentApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Keep test output readable: silence the per-request JSON log lines.
        patcher = mock.patch.object(main.Handler, "log_request", lambda *a, **k: None)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

        # Port 0 = let the OS pick a free port.
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), main.Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)

    def setUp(self):
        with main.LOCK:
            main.APPOINTMENTS.clear()

    def call(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    # --- health and routing ---

    def test_health_returns_ok_and_version(self):
        status, body = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "version": main.VERSION})

    def test_health_ignores_query_string(self):
        status, _ = self.call("GET", "/health?probe=1")
        self.assertEqual(status, 200)

    def test_unknown_path_returns_404_json(self):
        status, body = self.call("GET", "/nope")
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "not found"})

    # --- booking ---

    def test_create_appointment(self):
        status, body = self.call("POST", "/appointments", GOOD)
        self.assertEqual(status, 201)
        self.assertEqual(body["patient_id"], "p-1001")
        self.assertEqual(body["provider_id"], "dr-42")
        self.assertEqual(body["status"], "booked")
        self.assertTrue(body["id"])

    def test_get_and_list_appointment(self):
        _, created = self.call("POST", "/appointments", GOOD)
        status, fetched = self.call("GET", f"/appointments/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched, created)
        status, listing = self.call("GET", "/appointments")
        self.assertEqual(status, 200)
        self.assertEqual(listing["appointments"], [created])

    def test_unknown_appointment_returns_404(self):
        status, _ = self.call("GET", "/appointments/does-not-exist")
        self.assertEqual(status, 404)

    # --- conflicts ---

    def test_double_booking_same_provider_and_slot_returns_409(self):
        self.call("POST", "/appointments", GOOD)
        status, _ = self.call("POST", "/appointments", {**GOOD, "patient_id": "p-2002"})
        self.assertEqual(status, 409)

    def test_same_instant_in_other_timezone_returns_409(self):
        self.call("POST", "/appointments", GOOD)
        other_tz = {**GOOD, "slot": "2026-11-02T10:00:00-05:00"}  # same instant as 15:00Z
        status, _ = self.call("POST", "/appointments", other_tz)
        self.assertEqual(status, 409)

    def test_same_slot_different_provider_is_allowed(self):
        self.call("POST", "/appointments", GOOD)
        status, _ = self.call("POST", "/appointments", {**GOOD, "provider_id": "dr-43"})
        self.assertEqual(status, 201)

    # --- validation ---

    def test_slot_without_timezone_returns_400(self):
        status, _ = self.call("POST", "/appointments", {**GOOD, "slot": "2026-11-02T15:00:00"})
        self.assertEqual(status, 400)

    def test_missing_fields_return_400(self):
        status, _ = self.call("POST", "/appointments", {"patient_id": "p-1001"})
        self.assertEqual(status, 400)

    def test_invalid_json_returns_400(self):
        status, _ = self.call("POST", "/appointments", raw=b"{not json")
        self.assertEqual(status, 400)

    def test_oversized_body_returns_413(self):
        # Declare a body larger than the limit without sending it, so the
        # server's response is deterministic.
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.putrequest("POST", "/appointments")
        conn.putheader("Content-Length", str(main.MAX_BODY_BYTES + 1))
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 413)
        conn.close()


if __name__ == "__main__":
    unittest.main()
