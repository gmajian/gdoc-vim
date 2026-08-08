# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""gdoc-vim: edit Google Docs as Markdown in your terminal editor."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Single source of truth: the version declared in pyproject.toml.
    __version__ = version("gdoc-vim")
except PackageNotFoundError:  # running from a source tree, not installed
    __version__ = "0+unknown"
