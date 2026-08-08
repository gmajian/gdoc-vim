# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Tests for URL parsing and the Drive wrappers."""

from __future__ import annotations

import pytest

from gdoc_vim.drive import (
    create_doc,
    doc_url,
    export_markdown,
    extract_file_id,
    get_doc_metadata,
    rename_doc,
    update_markdown,
)

FILE_ID = "13axzxdpQsNSE_bZ1nUyW5yKAkru_xz2zzBzRiawNls8"


@pytest.mark.parametrize(
    "value",
    [
        f"https://docs.google.com/document/d/{FILE_ID}/edit",
        f"https://docs.google.com/document/d/{FILE_ID}/edit?tab=t.0",
        f"https://docs.google.com/document/u/0/d/{FILE_ID}/edit",
        f"https://docs.google.com/document/u/3/d/{FILE_ID}/edit?usp=sharing",
        f"http://docs.google.com/document/d/{FILE_ID}/",
        FILE_ID,
        f"  {FILE_ID}  ",
    ],
)
def test_extract_file_id_accepts_url_shapes(value):
    assert extract_file_id(value) == FILE_ID


def test_extract_file_id_rejects_url_without_id():
    with pytest.raises(ValueError, match="No document id"):
        extract_file_id("https://example.com/not-a-doc")


def test_doc_url_round_trips():
    assert extract_file_id(doc_url(FILE_ID)) == FILE_ID


def test_get_doc_metadata(service):
    meta = get_doc_metadata(service, "DOC1")
    assert meta["name"] == "Test Doc"


def test_export_markdown_returns_text(service):
    assert export_markdown(service, "DOC1") == "# Title\n\nbody\n"


def test_export_markdown_rejects_non_doc(service, store):
    store["SHEET"] = {
        "name": "A Sheet",
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "content": "",
    }
    with pytest.raises(ValueError, match="not a Google Doc"):
        export_markdown(service, "SHEET")


def test_create_doc(service, store):
    file_id = create_doc(service, "Brand New")
    assert store[file_id]["name"] == "Brand New"
    assert store[file_id]["content"] == ""


def test_rename_doc_keeps_content(service, store):
    rename_doc(service, "DOC1", "Renamed")
    assert store["DOC1"]["name"] == "Renamed"
    assert store["DOC1"]["content"] == "# Title\n\nbody\n"


def test_update_markdown_replaces_body(service, store):
    update_markdown(service, "DOC1", "# Replaced\n")
    assert store["DOC1"]["content"] == "# Replaced\n"
    assert store["DOC1"]["name"] == "Test Doc"


def test_update_markdown_handles_unicode(service, store):
    update_markdown(service, "DOC1", "# 标题\n\n中文正文\n")
    assert store["DOC1"]["content"] == "# 标题\n\n中文正文\n"
