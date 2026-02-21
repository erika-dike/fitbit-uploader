#!/usr/bin/env python3
"""Lightweight HTTP server to trigger Fitbit data fetch from a browser."""

import hmac
import traceback
from datetime import date
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import config
import fitbit_client
import sheets_writer


class FetchHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path != "/fetch":
            self._respond(404, "Not found. Use /fetch?key=YOUR_API_KEY")
            return

        params = parse_qs(parsed.query)
        key = params.get("key", [None])[0]

        if not key or not hmac.compare_digest(key, config.API_KEY):
            self._respond(403, "Forbidden: invalid or missing API key.")
            return

        # Determine target date
        raw_date = params.get("date", [None])[0]
        try:
            target = date.fromisoformat(raw_date) if raw_date else date.today()
        except ValueError:
            self._respond(400, f"Bad date format: {raw_date}. Use YYYY-MM-DD.")
            return

        # Run the fetch + write pipeline
        try:
            metrics = fitbit_client.fetch_all(target)
            sheets_writer.append_fitbit(metrics)
        except Exception:
            self._respond(500, f"Error:\n{traceback.format_exc()}")
            return

        summary = "\n".join(f"  {k}: {v}" for k, v in metrics.items())
        self._respond(200, f"OK — Fitbit data for {target} written to sheet.\n\n{summary}")

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, fmt, *args):
        # Default format but prefixed for clarity
        print(f"[server] {args[0]} {args[1]} {args[2]}")


def main():
    config._ensure_loaded()
    addr = ("0.0.0.0", config.SERVER_PORT)
    server = HTTPServer(addr, FetchHandler)
    print(f"Listening on {addr[0]}:{addr[1]}  —  GET /fetch?key=...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
