#!/usr/bin/env python3

import json
import os
import socketserver
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

import analyze_tpms
import vehicle_map_editor
from vehicle_map_editor import VehicleMapEditError

SERVICE_PORT = int(os.environ.get("TPMS_SERVICE_PORT", 8099))

_run_lock = threading.Lock()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class TPMSHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in CORS_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for name, value in CORS_HEADERS.items():
            self.send_header(name, value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"ok": True, "service": "tpms_analyzer"})
        else:
            self.send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self):
        if self.path == "/refresh":
            self._handle_refresh()
        elif self.path == "/vehicle-map-edit":
            self._handle_vehicle_map_edit()
        else:
            self.send_json(404, {"ok": False, "error": "Not found"})

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _handle_refresh(self):
        print("TPMS service: refresh requested", flush=True)

        if not _run_lock.acquire(blocking=False):
            self.send_json(503, {"ok": False, "error": "Analysis already in progress"})
            return

        try:
            analyze_tpms.main()
            print("TPMS service: refresh complete", flush=True)
            self.send_json(200, {"ok": True, "action": "refresh"})
        except Exception as exc:
            print(f"TPMS service: refresh error: {exc}", flush=True)
            traceback.print_exc()
            self.send_json(500, {"ok": False, "error": str(exc)})
        finally:
            _run_lock.release()

    def _handle_vehicle_map_edit(self):
        print("TPMS service: vehicle-map-edit requested", flush=True)

        if not _run_lock.acquire(blocking=False):
            self.send_json(503, {"ok": False, "error": "Analysis already in progress"})
            return

        response = None
        try:
            raw = self._read_body()
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, ValueError) as exc:
                response = (400, {"ok": False, "error": f"Invalid JSON: {exc}"})
                return

            try:
                result = vehicle_map_editor.apply_payload(payload)
            except VehicleMapEditError as exc:
                response = (400, {"ok": False, "error": str(exc)})
                return

            try:
                analyze_tpms.main()
            except Exception as exc:
                print(f"TPMS service: re-analyze after edit failed: {exc}", flush=True)
                traceback.print_exc()
                response = (500, {"ok": False, "error": f"Edit saved but re-analyze failed: {exc}"})
                return

            print(f"TPMS service: vehicle-map-edit complete: {result.get('action')}", flush=True)
            response = (200, {"ok": True, "action": "vehicle-map-edit", "edit": result})

        except Exception as exc:
            print(f"TPMS service: vehicle-map-edit unexpected error: {exc}", flush=True)
            traceback.print_exc()
            response = (500, {"ok": False, "error": str(exc)})

        finally:
            _run_lock.release()
            if response is not None:
                self.send_json(*response)


def main():
    server = ThreadedHTTPServer(("0.0.0.0", SERVICE_PORT), TPMSHandler)
    print(f"TPMS service: listening on 0.0.0.0:{SERVICE_PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
