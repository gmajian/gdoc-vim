# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""First-run setup guidance."""

from __future__ import annotations

from pathlib import Path

CONSOLE_URL = "https://console.cloud.google.com/"


class MissingClientSecretsError(Exception):
    """No OAuth client configured; carries where it should go."""

    def __init__(self, dest: Path):
        self.dest = dest
        super().__init__(f"No OAuth client credentials found (expected {dest}).")


def setup_guide(dest: Path) -> str:
    """Return step-by-step instructions for creating an OAuth client."""
    return f"""\
gdoc-vim needs a Google OAuth client before it can talk to your Google Docs.
This is a one-time setup and takes about 3 minutes.

  1. Open the Google Cloud Console:
       {CONSOLE_URL}

  2. Create a project (top-left project dropdown -> New Project).
     Any name works, e.g. "gdoc-vim".

  3. Enable the two APIs, clicking ENABLE on each page:

       https://console.cloud.google.com/apis/library/drive.googleapis.com
       https://console.cloud.google.com/apis/library/docs.googleapis.com

     Drive is required. Docs is only used to warn you before
     flattening a multi-tab document.

  4. Configure the consent screen:
     "APIs & Services -> OAuth consent screen"
     (newer console: "Google Auth Platform -> Branding")
       - User type: External
       - Fill in app name and your own email where required
       - Add your own Google address under "Test users", or
         sign-in will be refused.

     Then set the publishing status to "In production"
     (newer console: "Google Auth Platform -> Audience").
     This needs no verification, and avoids the 7-day refresh
     token expiry that clients left in "Testing" get -- which
     would make you sign in again every week.

  5. Create the client:
     "Credentials -> Create credentials -> OAuth client ID"
       - Application type: Desktop app
       - Click Create, then download the JSON.

  6. Move the downloaded file to:
       {dest}

     Alternatively, point gdoc-vim at it directly without moving it:
       export GDOC_VIM_CLIENT_SECRETS=/path/to/downloaded.json

Then run gdoc-vim again. A browser will open once to sign in, and your
login is cached afterwards.

Note: because this client is unverified, Google shows a warning screen at
sign-in. Click "Advanced" -> "Go to ... (unsafe)" to continue. That warning
is expected for a personal OAuth client.
"""
