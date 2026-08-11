# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Tests for argument validation and the end-to-end command workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from gdoc_vim import cli
from gdoc_vim.onboarding import MissingClientSecretsError


@pytest.fixture
def run(service, monkeypatch):
    """Invoke cli.run() with the fake Drive service and default arguments."""
    monkeypatch.setattr(cli, "build_drive_service", lambda **kw: service)

    def _run(**overrides):
        args = dict(
            doc=None,
            new=None,
            title=None,
            edit=False,
            output=None,
            push=None,
            confirm=False,
            reauth=False,
            no_browser=False,
            port=None,
        )
        args.update(overrides)
        return cli.run(argparse.Namespace(**args))

    return _run


# --- argument validation -------------------------------------------------


@pytest.mark.parametrize(
    "argv, message",
    [
        ([], "provide a Google Doc URL"),
        (["DOC1", "-n", "Title"], "not both"),
        (["-n", "Title", "-t", "Other"], "redundant"),
        (["DOC1", "-o", "a.md", "-p", "b.md"], "mutually exclusive"),
    ],
)
def test_invalid_argument_combinations(argv, message, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2
    assert message in capsys.readouterr().err


# --- the default edit workflow -------------------------------------------


def test_edit_uploads_on_save(run, store, fake_editor):
    fake_editor("# Rewritten\n")
    assert run(doc="DOC1") == 0
    assert store["DOC1"]["content"] == "# Rewritten\n"


def test_edit_accepts_full_url(run, store, fake_editor):
    fake_editor("# Via URL\n")
    url = "https://docs.google.com/document/d/DOC1/edit?tab=t.0"
    assert run(doc=url) == 0
    assert store["DOC1"]["content"] == "# Via URL\n"


def test_edit_skips_upload_when_unchanged(run, store, fake_editor):
    fake_editor(None)
    assert run(doc="DOC1") == 0
    assert store["DOC1"]["content"] == "# Title\n\nbody\n"


# --- creating and renaming ------------------------------------------------


def test_new_creates_then_edits(run, store, fake_editor):
    fake_editor("# Fresh content\n")
    assert run(new="Fresh Doc") == 0
    created = [d for d in store.values() if d["name"] == "Fresh Doc"]
    assert created and created[0]["content"] == "# Fresh content\n"


def test_title_renames_without_opening_editor(run, store, fake_editor):
    fake_editor("# Should not be written\n")
    assert run(doc="DOC1", title="Renamed") == 0
    assert store["DOC1"]["name"] == "Renamed"
    assert store["DOC1"]["content"] == "# Title\n\nbody\n"


def test_title_with_edit_does_both(run, store, fake_editor):
    fake_editor("# Both\n")
    assert run(doc="DOC1", title="Renamed", edit=True) == 0
    assert store["DOC1"]["name"] == "Renamed"
    assert store["DOC1"]["content"] == "# Both\n"


def test_title_with_output_does_both(run, store, tmp_path):
    out = tmp_path / "out.md"
    assert run(doc="DOC1", title="Renamed", output=str(out)) == 0
    assert store["DOC1"]["name"] == "Renamed"
    assert out.read_text(encoding="utf-8") == "# Title\n\nbody\n"


# --- non-interactive export / import --------------------------------------


def test_output_exports_without_editor(run, tmp_path):
    out = tmp_path / "notes.md"
    assert run(doc="DOC1", output=str(out)) == 0
    assert out.read_text(encoding="utf-8") == "# Title\n\nbody\n"


def test_push_uploads_file(run, store, tmp_path):
    src = tmp_path / "in.md"
    src.write_text("# From file\n", encoding="utf-8")
    assert run(doc="DOC1", push=str(src)) == 0
    assert store["DOC1"]["content"] == "# From file\n"


def test_push_missing_file_fails(run, store, tmp_path):
    assert run(doc="DOC1", push=str(tmp_path / "nope.md")) == 1
    assert store["DOC1"]["content"] == "# Title\n\nbody\n"


# --- confirmation mode ----------------------------------------------------


def test_confirm_declined_leaves_document_alone(run, store, fake_editor, monkeypatch):
    fake_editor("# Rewritten\n")
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert run(doc="DOC1", confirm=True) == 1
    assert store["DOC1"]["content"] == "# Title\n\nbody\n"


def test_confirm_accepted_uploads(run, store, fake_editor, monkeypatch):
    fake_editor("# Rewritten\n")
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert run(doc="DOC1", confirm=True) == 0
    assert store["DOC1"]["content"] == "# Rewritten\n"


def test_confirm_shows_diff(run, store, fake_editor, monkeypatch, capsys):
    fake_editor("# Rewritten\n")
    monkeypatch.setattr("builtins.input", lambda _: "n")
    run(doc="DOC1", confirm=True)
    err = capsys.readouterr().err
    assert "-# Title" in err and "+# Rewritten" in err


def test_confirm_on_push_declined(run, store, tmp_path, monkeypatch):
    src = tmp_path / "in.md"
    src.write_text("# From file\n", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert run(doc="DOC1", push=str(src), confirm=True) == 1
    assert store["DOC1"]["content"] == "# Title\n\nbody\n"


# --- error handling in main() ---------------------------------------------


def test_missing_client_secrets_prints_setup_guide(monkeypatch, capsys):
    def boom(**kwargs):
        raise MissingClientSecretsError(Path("/tmp/credentials.json"))

    monkeypatch.setattr(cli, "build_drive_service", boom)
    assert cli.main(["-n", "Doc"]) == 1
    err = capsys.readouterr().err
    assert "Google Cloud Console" in err
    assert "/tmp/credentials.json" in err


def test_keyboard_interrupt_returns_130(monkeypatch):
    def boom(**kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "build_drive_service", boom)
    assert cli.main(["DOC1"]) == 130
