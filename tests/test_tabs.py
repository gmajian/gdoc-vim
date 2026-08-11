# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Tests for refusing to flatten a multi-tab document."""

from __future__ import annotations

import argparse

import pytest
from googleapiclient.errors import HttpError

from gdoc_vim import cli, docs


class _FakeDocs:
    """Stand-in for the Docs v1 client; raises `error` when given one."""

    def __init__(self, tabs=None, error=None):
        self._tabs = tabs if tabs is not None else []
        self._error = error
        self.fields_requested = None

    def documents(self):
        return self

    def get(self, documentId, includeTabsContent, fields):
        self.fields_requested = fields
        return self

    def execute(self):
        if self._error:
            raise self._error
        return {"tabs": self._tabs}


def _tab(*children):
    return {"tabProperties": {"tabId": "t"}, "childTabs": list(children)}


def _http_error(status):
    resp = type("R", (), {"status": status, "reason": "denied"})()
    return HttpError(resp, b"{}")


# --- counting -------------------------------------------------------------


def test_no_tabs_field_counts_zero():
    assert docs.count_tabs(_FakeDocs([]), "ID") == 0


def test_single_tab():
    assert docs.count_tabs(_FakeDocs([_tab()]), "ID") == 1


def test_several_tabs():
    assert docs.count_tabs(_FakeDocs([_tab(), _tab(), _tab()]), "ID") == 3


def test_nested_child_tabs_are_counted():
    assert docs.count_tabs(_FakeDocs([_tab(_tab(_tab()))]), "ID") == 3


def test_api_error_returns_none_instead_of_raising():
    # 403 is what a project without the Docs API enabled returns.
    assert docs.count_tabs(_FakeDocs(error=_http_error(403)), "ID") is None


def test_only_tab_metadata_is_requested():
    fake = _FakeDocs([_tab()])
    docs.count_tabs(fake, "ID")
    assert "tabProperties" in fake.fields_requested
    assert "body" not in fake.fields_requested


# --- the guard in the CLI -------------------------------------------------


@pytest.fixture
def docs_service(monkeypatch):
    """Install a fake Docs client; call the returned setter to configure it."""
    holder = {}

    def _set(tabs=None, error=None):
        holder["svc"] = _FakeDocs(tabs, error)

    _set([_tab()])
    monkeypatch.setattr(cli, "build_docs_service", lambda: holder["svc"])
    return _set


@pytest.fixture
def run(service, monkeypatch):
    monkeypatch.setattr(cli, "build_drive_service", lambda **kw: service)

    def _run(**overrides):
        args = dict(
            doc="DOC1", new=None, title=None, edit=False, output=None,
            push=None, confirm=False, reauth=False, no_browser=False,
            port=None, force=False,
        )
        args.update(overrides)
        return cli.run(argparse.Namespace(**args))

    return _run


def test_edit_refuses_on_multiple_tabs(run, store, docs_service, fake_editor):
    docs_service([_tab(), _tab()])
    fake_editor("# Rewritten\n")

    assert run() == 1
    assert store["DOC1"]["content"] == "# Title\n\nbody\n"


def test_editor_never_opens_when_refusing(run, docs_service, monkeypatch):
    docs_service([_tab(), _tab()])
    opened = []
    monkeypatch.setattr(cli, "edit_text", lambda text: opened.append(text) or text)

    run()
    assert not opened, "the editor must not open for a document we cannot save"


def test_force_allows_flattening(run, store, docs_service, fake_editor):
    docs_service([_tab(), _tab()])
    fake_editor("# Rewritten\n")

    assert run(force=True) == 0
    assert store["DOC1"]["content"] == "# Rewritten\n"


def test_single_tab_proceeds(run, store, docs_service, fake_editor):
    docs_service([_tab()])
    fake_editor("# Rewritten\n")

    assert run() == 0
    assert store["DOC1"]["content"] == "# Rewritten\n"


def test_push_from_file_is_guarded(run, store, docs_service, tmp_path):
    docs_service([_tab(), _tab()])
    src = tmp_path / "in.md"
    src.write_text("# From file\n", encoding="utf-8")

    assert run(push=str(src)) == 1
    assert store["DOC1"]["content"] == "# Title\n\nbody\n"


def test_export_is_not_guarded(run, docs_service, tmp_path):
    """Exporting changes nothing remotely, so it must still work."""
    docs_service([_tab(), _tab()])
    out = tmp_path / "out.md"

    assert run(output=str(out)) == 0
    assert out.read_text(encoding="utf-8") == "# Title\n\nbody\n"


def test_unavailable_check_warns_and_continues(
    run, store, docs_service, fake_editor, capsys
):
    docs_service(error=_http_error(403))
    fake_editor("# Rewritten\n")

    assert run() == 0
    assert store["DOC1"]["content"] == "# Rewritten\n"
    assert "could not check" in capsys.readouterr().err
