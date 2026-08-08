# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Tests for the first-run setup guidance."""

from __future__ import annotations

from pathlib import Path

from gdoc_vim.onboarding import MissingClientSecretsError, setup_guide

DEST = Path("/home/someone/.config/gdoc-vim/credentials.json")


def test_error_carries_destination():
    err = MissingClientSecretsError(DEST)
    assert err.dest == DEST
    assert str(DEST) in str(err)


def test_guide_names_the_destination_path():
    assert str(DEST) in setup_guide(DEST)


def test_guide_covers_each_setup_step():
    guide = setup_guide(DEST)
    for fragment in [
        "console.cloud.google.com",
        "Google Drive API",
        "OAuth consent screen",
        "Test users",
        "In production",
        "Desktop app",
        "GDOC_VIM_CLIENT_SECRETS",
    ]:
        assert fragment in guide, f"setup guide no longer mentions {fragment!r}"


def test_guide_warns_about_the_unverified_app_screen():
    guide = setup_guide(DEST)
    assert "unverified" in guide
    assert "7-day" in guide or "7 day" in guide
