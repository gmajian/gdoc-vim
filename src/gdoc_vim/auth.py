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


def get_credentials(*, interactive: bool = True, force: bool = False) -> Credentials:
    """Return credentials, running the browser flow if needed."""
    if not force:
        creds = _load_cached_credentials()
        if creds:
            return creds

    if not interactive:
        raise RuntimeError("Not authorized and running non-interactively.")

    client_config = _load_client_config()

    # An unannounced browser popup plus Google's "unverified app" screen is
    # alarming without warning.
    print(
        'Opening your browser to sign in to Google (one-time).\n'
        'If you see an "unverified app" warning, click Advanced -> '
        "Go to gdoc-vim (unsafe) to continue.",
        file=sys.stderr,
    )

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)
    return creds


def build_drive_service(*, interactive: bool = True, force: bool = False):
    """Authenticated Drive v3 client."""
    creds = get_credentials(interactive=interactive, force=force)
    return build("drive", "v3", credentials=creds, cache_discovery=False)
