import json
import sys
import uuid
from datetime import timezone, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

PORT = 8000
VERSION = "1.0.0"
MAX_BODY_BYTES = 4096

# In-memory store. Demo only: data is lost on restart and is NOT shared
# between replicas. A real database is required before launch.
APPOINTMENTS = {}
LOCK = Lock()


def valid_id(value):
    """Opaque patient/provider IDs only: a non-empty string up to 64 chars."""
    return isinstance(value, str) and 0 < len(value) <= 64


def parse_slot(value):
    """Return the slot as a UTC ISO 8601 string, or None if invalid."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None  # require an explicit timezone
    return parsed.astimezone(timezone.utc).isoformat()


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, body):
        data = json.dumps(body, separators=(",", ":")).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_request(self, code="-", size="-"):
        # One JSON line per request. Deliberately omits the client IP and the
        # query string, which could contain personal data.
        entry = {
            "method": self.command,
            "path": self.path.split("?")[0],
            "status": code,
        }
        print(json.dumps(entry, separators=(",", ":")), file=sys.stderr, flush=True)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"  # ignore ?query=string
        if path == "/health":
            self.send_json(200, {"status": "ok", "version": VERSION})
        elif path == "/appointments":
            with LOCK:
                items = list(APPOINTMENTS.values())
            self.send_json(200, {"appointments": items})
        elif path.startswith("/appointments/"):
            appointment_id = path[len("/appointments/"):]
            with LOCK:
                appointment = APPOINTMENTS.get(appointment_id)
            if appointment is None:
                self.send_json(404, {"error": "not found"})
            else:
                self.send_json(200, appointment)
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        if path != "/appointments":
            self.send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            self.send_json(400, {"error": "request body required"})
            return
        if length > MAX_BODY_BYTES:
            self.send_json(413, {"error": "request body too large"})
            return

        try:
            payload = json.loads(self.rfile.read(length))
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "body must be a JSON object"})
            return

        patient_id = payload.get("patient_id")
        provider_id = payload.get("provider_id")
        slot = parse_slot(payload.get("slot"))
        if not (valid_id(patient_id) and valid_id(provider_id) and slot):
            self.send_json(
                400,
                {"error": "patient_id, provider_id and slot (ISO 8601 with timezone) are required"},
            )
            return

        with LOCK:
            taken = any(
                a["provider_id"] == provider_id and a["slot"] == slot
                for a in APPOINTMENTS.values()
            )
            if not taken:
                appointment = {
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "provider_id": provider_id,
                    "slot": slot,
                    "status": "booked",
                }
                APPOINTMENTS[appointment["id"]] = appointment

        if taken:
            self.send_json(409, {"error": "slot already booked for this provider"})
        else:
            self.send_json(201, appointment)


if __name__ == "__main__":
    # 0.0.0.0 = listen on all network interfaces, required inside a container
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
