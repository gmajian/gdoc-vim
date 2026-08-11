# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Google OAuth2, authorized lazily on first use.

Client credentials are resolved from, in order: $GDOC_VIM_CLIENT_SECRETS,
~/.config/gdoc-vim/credentials.json, then a client bundled with the package.
"""

from __future__ import annotations

import json
import os
import sys
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .onboarding import MissingClientSecretsError

# Full drive scope: the tool opens docs it did not create, which drive.file
# does not cover.
SCOPES = ["https://www.googleapis.com/auth/drive"]

DEFAULT_CONFIG_DIR = Path(
    os.environ.get("GDOC_VIM_CONFIG_DIR", Path.home() / ".config" / "gdoc-vim")
)

# Nothing listens on this port in the headless flow — it only has to be a
# loopback address, which is all a Desktop client may redirect to.
DEFAULT_CALLBACK_PORT = 8080


def is_headless() -> bool:
    """True when this machine probably has no browser to open."""
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return True
    return sys.platform.startswith("linux") and not os.environ.get("DISPLAY")


def extract_code(pasted: str) -> str:
    """Pull the authorization code out of a pasted redirect URL.

    Accepts the whole address the browser landed on, or a bare code.
    """
    pasted = pasted.strip()
    if not pasted:
        raise RuntimeError("Nothing pasted; authorization cancelled.")
    if not pasted.startswith(("http://", "https://")):
        return pasted

    params = parse_qs(urlparse(pasted).query)
    if "error" in params:
        raise RuntimeError(f"Google reported: {params['error'][0]}")
    if "code" not in params:
        raise RuntimeError(
            "That address has no ?code= in it. Copy the full address the "
            "browser ended up on, starting with http://localhost/"
        )
    return params["code"][0]


def _headless_instructions(auth_url: str, port: int) -> str:
    return f"""
No browser here (this looks like a remote session), so finish sign-in by hand.

1. Open this URL in a browser on any machine:

{auth_url}

2. Approve access. The browser will then land on a "site can't be reached"
   page at localhost:{port} -- that is expected, nothing is running there.
   The address bar now holds your authorization code.

3. Copy that whole address and paste it below.
"""


def _config_dir() -> Path:
    d = DEFAULT_CONFIG_DIR
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    return d


def token_path() -> Path:
    return _config_dir() / "token.json"


def user_credentials_path() -> Path:
    return _config_dir() / "credentials.json"


def _load_client_config() -> dict:
    env_path = os.environ.get("GDOC_VIM_CLIENT_SECRETS")
    if env_path:
        return json.loads(Path(env_path).read_text())

    user_path = user_credentials_path()
    if user_path.exists():
        return json.loads(user_path.read_text())

    bundled = resources.files("gdoc_vim").joinpath("client_secret.json")
    if bundled.is_file():
        return json.loads(bundled.read_text(encoding="utf-8"))

    raise MissingClientSecretsError(user_path)


def _load_cached_credentials() -> Credentials | None:
    tok = token_path()
    if not tok.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(tok), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)
        return creds
    return None


def _save_credentials(creds: Credentials) -> None:
    tok = token_path()
    tok.write_text(creds.to_json())
    os.chmod(tok, 0o600)


def get_credentials(
    *,
    interactive: bool = True,
    force: bool = False,
    port: int | None = None,
    no_browser: bool | None = None,
) -> Credentials:
    """Return credentials, running the browser flow if needed.

    On a headless machine the browser is not opened; the URL is printed along
    with the ssh command that forwards the callback port.
    """
    if not force:
        creds = _load_cached_credentials()
        if creds:
            return creds

    if not interactive:
        raise RuntimeError("Not authorized and running non-interactively.")

    client_config = _load_client_config()

    if no_browser is None:
        no_browser = is_headless()
    if port is None:
        port = DEFAULT_CALLBACK_PORT if no_browser else 0

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    if no_browser:
        # Google killed the out-of-band flow, so the redirect still points at
        # loopback; the user copies the code out of the failed page's URL.
        flow.redirect_uri = f"http://localhost:{port}/"
        auth_url, _ = flow.authorization_url()
        print(_headless_instructions(auth_url, port), file=sys.stderr)
        code = extract_code(input("Paste the address here: "))
        flow.fetch_token(code=code)
        creds = flow.credentials
    else:
        # An unannounced browser popup plus Google's "unverified app" screen
        # is alarming without warning.
        print(
            "Opening your browser to sign in to Google (one-time).\n"
            'If you see an "unverified app" warning, click Advanced -> '
            "Go to gdoc-vim (unsafe) to continue.",
            file=sys.stderr,
        )
        creds = flow.run_local_server(port=port)

    _save_credentials(creds)
    return creds


def build_drive_service(
    *,
    interactive: bool = True,
    force: bool = False,
    port: int | None = None,
    no_browser: bool | None = None,
):
    """Authenticated Drive v3 client."""
    creds = get_credentials(
        interactive=interactive, force=force, port=port, no_browser=no_browser
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)
