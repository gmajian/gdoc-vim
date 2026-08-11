# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Docs API checks for structure the Markdown round trip would destroy."""

from __future__ import annotations

from googleapiclient.errors import HttpError

# Deep link to the Docs API in the Cloud Console library, which lands on the
# Enable button for whichever project the user has selected.
DOCS_API_ENABLE_URL = "https://console.cloud.google.com/apis/library/docs.googleapis.com"

# Only tab metadata is needed, not the content of every tab. Docs nests tabs a
# few levels deep, so ask for the same shape at each level.
_TAB_FIELDS = "tabs(tabProperties,childTabs(tabProperties,childTabs(tabProperties)))"


def _count(tabs: list) -> int:
    """Count tabs, including nested child tabs."""
    return sum(1 + _count(tab.get("childTabs", [])) for tab in tabs)


def count_tabs(service, file_id: str) -> int | None:
    """How many tabs a document has, or None when the check could not run.

    Returns None rather than raising when the Docs API is unavailable — the
    check is a safety net, not a requirement.
    """
    try:
        doc = (
            service.documents()
            .get(documentId=file_id, includeTabsContent=True, fields=_TAB_FIELDS)
            .execute()
        )
    except HttpError:
        return None
    return _count(doc.get("tabs", []))
