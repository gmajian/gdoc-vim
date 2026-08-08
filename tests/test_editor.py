# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Tests for editor resolution and the temp-file round trip."""

from __future__ import annotations

import subprocess

import pytest

from gdoc_vim.editor import edit_text, resolve_editor

EDITOR_VARS = ("GDOC_VIM_EDITOR", "VISUAL", "EDITOR")


@pytest.fixture
def no_editor_env(monkeypatch):
    for var in EDITOR_VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults_to_vim(no_editor_env):
    assert resolve_editor() == ["vim"]


def test_editor_precedence(no_editor_env, monkeypatch):
    monkeypatch.setenv("EDITOR", "nano")
    assert resolve_editor() == ["nano"]

    monkeypatch.setenv("VISUAL", "emacs")
    assert resolve_editor() == ["emacs"]

    monkeypatch.setenv("GDOC_VIM_EDITOR", "nvim")
    assert resolve_editor() == ["nvim"]


def test_editor_splits_arguments(no_editor_env, monkeypatch):
    monkeypatch.setenv("GDOC_VIM_EDITOR", "code --wait")
    assert resolve_editor() == ["code", "--wait"]


def test_edit_text_returns_saved_content(fake_editor):
    fake_editor("# Edited\n")
    assert edit_text("# Original\n") == "# Edited\n"


def test_edit_text_unchanged_when_editor_saves_nothing(fake_editor):
    fake_editor(None)
    assert edit_text("# Original\n") == "# Original\n"


def test_edit_text_preserves_unicode(fake_editor):
    fake_editor("# 中文标题\n")
    assert edit_text("# 原文\n") == "# 中文标题\n"


def test_edit_text_raises_when_editor_fails(fake_editor):
    fake_editor(None, fail=True)
    with pytest.raises(subprocess.CalledProcessError):
        edit_text("# Original\n")


def test_edit_text_removes_temp_file(fake_editor, monkeypatch):
    seen = []

    real_run = subprocess.run

    def spy(argv, **kwargs):
        seen.append(argv[-1])
        return real_run(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    fake_editor("# Edited\n")
    edit_text("# Original\n")

    assert seen, "editor was never invoked"
    from pathlib import Path

    assert not Path(seen[0]).exists()
