#!/usr/bin/env python3

import datetime
import json
import os
import socketserver
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

import analyze_tpms
import vehicle_map_editor
from tpms_config import REPORT_PATH
from vehicle_map_editor import VehicleMapEditError

SERVICE_PORT = int(os.environ.get("TPMS_SERVICE_PORT", 8099))

_run_lock = threading.Lock()

STATIC_PNGS = frozenset({
    "tiresignal-logo.png",
    "tiresignal-report-logo.png",
    "tiresignal-favicon-32.png",
    "tiresignal-favicon-180.png",
})

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _env_bool(name, default):
    value = os.environ.get(name, default)
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _parse_refresh_time(value):
    try:
        hour_text, minute_text = str(value).strip().split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (TypeError, ValueError):
        pass

    print(
        f"TPMS service: invalid scheduled refresh time {value!r}; falling back to 03:10",
        flush=True,
    )
    return 3, 10


def _scheduler_loop(hour, minute, initial_last_run_date):
    last_scheduled_run_date = initial_last_run_date
    print(f"TPMS service: scheduled refresh enabled at {hour:02d}:{minute:02d}", flush=True)

    while True:
        now = datetime.datetime.now()
        today = now.date()
        scheduled_time_reached = (now.hour, now.minute) >= (hour, minute)

        if scheduled_time_reached and last_scheduled_run_date != today:
            last_scheduled_run_date = today

            if not _run_lock.acquire(blocking=False):
                print(
                    "TPMS service: scheduled refresh skipped; analysis already in progress",
                    flush=True,
                )
            else:
                try:
                    print("TPMS service: scheduled refresh starting", flush=True)
                    analyze_tpms.main()
                    print("TPMS service: scheduled refresh complete", flush=True)
                except Exception as exc:
                    print(f"TPMS service: scheduled refresh error: {exc}", flush=True)
                    traceback.print_exc()
                finally:
                    _run_lock.release()

        time.sleep(30)


def _start_scheduler():
    enabled = _env_bool("TPMS_SCHEDULED_REFRESH_ENABLED", "true")
    if not enabled:
        print("TPMS service: scheduled refresh disabled", flush=True)
        return

    hour, minute = _parse_refresh_time(os.environ.get("TPMS_SCHEDULED_REFRESH_TIME", "03:10"))
    now = datetime.datetime.now()
    initial_last_run_date = None
    if (now.hour, now.minute) >= (hour, minute):
        initial_last_run_date = now.date()

    thread = threading.Thread(
        target=_scheduler_loop,
        args=(hour, minute, initial_last_run_date),
        daemon=True,
    )
    thread.start()


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

    def send_png(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, code, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in CORS_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_static_png(self, filename):
        png_path = REPORT_PATH.parent / filename
        if not png_path.exists():
            self.send_json(404, {"ok": False, "error": "Asset not found"})
            return
        try:
            body = png_path.read_bytes()
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
            return
        self.send_png(body)

    def _send_report(self):
        if not REPORT_PATH.exists():
            self.send_json(404, {"ok": False, "error": "Report has not been generated yet"})
            return
        try:
            body = REPORT_PATH.read_bytes()
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})
            return
        self.send_html(200, body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"ok": True, "service": "tpms_analyzer"})
        elif self.path in ("/", "/report"):
            self._send_report()
        elif self.path.lstrip("/") in STATIC_PNGS:
            self._send_static_png(self.path.lstrip("/"))
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
    _start_scheduler()
    server.serve_forever()


if __name__ == "__main__":
    main()
