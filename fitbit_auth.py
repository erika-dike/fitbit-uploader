"""Fitbit OAuth2 Authorization Code flow with PKCE + token persistence."""

import base64
import hashlib
import json
import os
import secrets
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests
from requests_oauthlib import OAuth2Session

import config


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def _generate_pkce():
    """Generate code_verifier and code_challenge for PKCE."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


# ---------------------------------------------------------------------------
# Local callback server (captures the auth code from the redirect)
# ---------------------------------------------------------------------------

class _CallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth redirect and extracts the authorization code."""

    auth_code = None
    error = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            _CallbackHandler.auth_code = query["code"][0]
            self._respond("Authorization successful! You can close this tab.")
        else:
            _CallbackHandler.error = query.get("error", ["unknown"])[0]
            self._respond(f"Authorization failed: {_CallbackHandler.error}")

    def _respond(self, message):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(f"<html><body><h2>{message}</h2></body></html>".encode())

    def log_message(self, format, *args):
        pass  # silence request logs


def _wait_for_callback():
    """Start a local HTTP server and wait for the OAuth callback."""
    server = HTTPServer(("127.0.0.1", 8080), _CallbackHandler)
    server.timeout = 120  # wait up to 2 minutes
    _CallbackHandler.auth_code = None
    _CallbackHandler.error = None
    server.handle_request()
    server.server_close()
    if _CallbackHandler.error:
        raise RuntimeError(f"OAuth error: {_CallbackHandler.error}")
    if not _CallbackHandler.auth_code:
        raise RuntimeError("No authorization code received (timed out).")
    return _CallbackHandler.auth_code


# ---------------------------------------------------------------------------
# Token persistence
# ---------------------------------------------------------------------------

def _save_token(token):
    with open(config.FITBIT_TOKEN_FILE, "w") as f:
        json.dump(token, f, indent=2)


def _load_token():
    if not os.path.exists(config.FITBIT_TOKEN_FILE):
        return None
    with open(config.FITBIT_TOKEN_FILE) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def authorize():
    """Run the full OAuth2 browser flow. Returns a token dict."""
    config._ensure_loaded()
    verifier, challenge = _generate_pkce()

    session = OAuth2Session(
        config.FITBIT_CLIENT_ID,
        redirect_uri=config.FITBIT_REDIRECT_URI,
        scope=config.FITBIT_SCOPES,
    )

    auth_url, _ = session.authorization_url(
        config.FITBIT_AUTH_URI,
        code_challenge=challenge,
        code_challenge_method="S256",
    )

    print(f"\nOpening browser for Fitbit authorization...\n")
    print(f"If the browser doesn't open, visit this URL manually:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for callback...")
    code = _wait_for_callback()

    # Exchange code for tokens
    token = session.fetch_token(
        config.FITBIT_TOKEN_URI,
        code=code,
        code_verifier=verifier,
        client_secret=config.FITBIT_CLIENT_SECRET,
    )

    _save_token(token)
    print("Authorization successful! Tokens saved.")
    return token


def get_session():
    """Return an OAuth2Session with a valid access token (auto-refreshes if needed)."""
    config._ensure_loaded()
    token = _load_token()
    if token is None:
        print("No tokens found. Run 'python main.py auth' first.")
        raise SystemExit(1)

    def _token_updater(new_token):
        _save_token(new_token)

    session = OAuth2Session(
        config.FITBIT_CLIENT_ID,
        token=token,
        auto_refresh_url=config.FITBIT_TOKEN_URI,
        auto_refresh_kwargs={
            "client_id": config.FITBIT_CLIENT_ID,
            "client_secret": config.FITBIT_CLIENT_SECRET,
        },
        token_updater=_token_updater,
    )

    return session
