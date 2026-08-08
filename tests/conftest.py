# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Shared fixtures: an in-memory Drive stand-in and a scriptable fake editor."""

from __future__ import annotations

import sys

import pytest

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"

# Overwrites the file it is given with $FAKE_EDITOR_CONTENT, or leaves it
# untouched when that variable is unset. Exits non-zero if $FAKE_EDITOR_FAIL.
_FAKE_EDITOR = """\
import os, sys
if os.environ.get("FAKE_EDITOR_FAIL"):
    sys.exit(1)
content = os.environ.get("FAKE_EDITOR_CONTENT")
if content is not None:
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        fh.write(content)
"""


class FakeFiles:
    """Stand-in for `service.files()` covering the calls gdoc-vim makes."""

    def __init__(self, store: dict):
        self.store = store

    def get(self, fileId, fields):
        doc = self.store[fileId]
        return _Request(
            {"id": fileId, "name": doc["name"], "mimeType": doc["mimeType"]}
        )

    def export(self, fileId, mimeType):
        return _Request(self.store[fileId]["content"].encode("utf-8"))

    def create(self, body, fields):
        file_id = f"id-{len(self.store) + 1}"
        self.store[file_id] = {
            "name": body["name"],
            "mimeType": body["mimeType"],
            "content": "",
        }
        return _Request({"id": file_id})

    def update(self, fileId, fields, media_body=None, body=None):
        doc = self.store[fileId]
        if body and "name" in body:
            doc["name"] = body["name"]
        if media_body is not None:
            handle = media_body._fd
            handle.seek(0)
            doc["content"] = handle.read().decode("utf-8")
        return _Request({"id": fileId})


class _Request:
    """Mimics the googleapiclient request object's deferred `execute()`."""

    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class FakeService:
    def __init__(self, store: dict):
        self.store = store

    def files(self):
        return FakeFiles(self.store)


@pytest.fixture
def store():
    """Document store seeded with one Google Doc under id 'DOC1'."""
    return {
        "DOC1": {
            "name": "Test Doc",
            "mimeType": GOOGLE_DOC_MIME,
            "content": "# Title\n\nbody\n",
        }
    }


@pytest.fixture
def service(store):
    return FakeService(store)


@pytest.fixture
def fake_editor(tmp_path, monkeypatch):
    """Install a scripted editor; call the returned function to set its output.

    Passing None means "the user saved without changing anything".
    """
    script = tmp_path / "fake_editor.py"
    script.write_text(_FAKE_EDITOR, encoding="utf-8")
    monkeypatch.setenv("GDOC_VIM_EDITOR", f"{sys.executable} {script}")

    def _set(content: str | None, *, fail: bool = False):
        monkeypatch.delenv("FAKE_EDITOR_CONTENT", raising=False)
        monkeypatch.delenv("FAKE_EDITOR_FAIL", raising=False)
        if content is not None:
            monkeypatch.setenv("FAKE_EDITOR_CONTENT", content)
        if fail:
            monkeypatch.setenv("FAKE_EDITOR_FAIL", "1")

    return _set


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Keep every test away from the real ~/.config/gdoc-vim."""
    from gdoc_vim import auth

    monkeypatch.setattr(auth, "DEFAULT_CONFIG_DIR", tmp_path / "config")
    monkeypatch.delenv("GDOC_VIM_CLIENT_SECRETS", raising=False)
