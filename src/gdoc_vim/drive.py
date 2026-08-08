# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Drive API helpers for round-tripping a Doc through Markdown."""

from __future__ import annotations

import io
import re

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

MARKDOWN_MIME = "text/markdown"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"

# .../document/d/<id>/... and .../document/u/0/d/<id>/...
_DOC_ID_RE = re.compile(r"/document/(?:u/\d+/)?d/([a-zA-Z0-9_-]+)")


def extract_file_id(url_or_id: str) -> str:
    """Pull the file id out of a Docs URL, or pass through a bare id."""
    s = url_or_id.strip()
    match = _DOC_ID_RE.search(s)
    if match:
        return match.group(1)
    if s.startswith(("http://", "https://")):
        raise ValueError(f"No document id found in URL: {url_or_id!r}")
    return s


def get_doc_metadata(service, file_id: str) -> dict:
    """Fetch id, name and mimeType for a file."""
    return service.files().get(fileId=file_id, fields="id, name, mimeType").execute()


def create_doc(service, title: str) -> str:
    """Create an empty Doc, returning its id."""
    body = {"name": title, "mimeType": GOOGLE_DOC_MIME}
    return service.files().create(body=body, fields="id").execute()["id"]


def rename_doc(service, file_id: str, title: str) -> None:
    """Change a Doc's title."""
    service.files().update(fileId=file_id, body={"name": title}, fields="id").execute()


def export_markdown(service, file_id: str) -> str:
    """Export a Doc's content as Markdown."""
    meta = get_doc_metadata(service, file_id)
    if meta.get("mimeType") != GOOGLE_DOC_MIME:
        raise ValueError(
            f"{meta.get('name')!r} is not a Google Doc "
            f"(mimeType={meta.get('mimeType')!r})."
        )
    data = service.files().export(fileId=file_id, mimeType=MARKDOWN_MIME).execute()
    return data.decode("utf-8") if isinstance(data, bytes) else data


def update_markdown(service, file_id: str, markdown_text: str) -> None:
    """Replace a Doc's body with Markdown, keeping its id and sharing."""
    buffer = io.BytesIO(markdown_text.encode("utf-8"))
    media = MediaIoBaseUpload(buffer, mimetype=MARKDOWN_MIME, resumable=False)
    service.files().update(fileId=file_id, media_body=media, fields="id").execute()


def doc_url(file_id: str) -> str:
    """Canonical edit URL for a document id."""
    return f"https://docs.google.com/document/d/{file_id}/edit"


__all__ = [
    "HttpError",
    "extract_file_id",
    "get_doc_metadata",
    "create_doc",
    "rename_doc",
    "export_markdown",
    "update_markdown",
    "doc_url",
]
