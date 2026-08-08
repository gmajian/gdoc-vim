# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Guard against the reported version drifting from the packaged one."""

from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

import gdoc_vim
from gdoc_vim import cli

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_version_matches_installed_distribution():
    assert gdoc_vim.__version__ == version("gdoc-vim")


@pytest.mark.skipif(not PYPROJECT.exists(), reason="not a source checkout")
def test_version_matches_pyproject():
    declared = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    assert gdoc_vim.__version__ == declared


def test_cli_reports_the_same_version(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert gdoc_vim.__version__ in capsys.readouterr().out
