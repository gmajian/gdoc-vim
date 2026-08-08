# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Launch the user's terminal editor on a temporary file."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path


def resolve_editor() -> list[str]:
    """Editor command as argv: $GDOC_VIM_EDITOR, $VISUAL, $EDITOR, else vim."""
    for var in ("GDOC_VIM_EDITOR", "VISUAL", "EDITOR"):
        value = os.environ.get(var)
        if value:
            return shlex.split(value)
    return ["vim"]


def edit_text(initial: str, *, suffix: str = ".md") -> str:
    """Edit `initial` in the editor and return what was saved."""
    editor = resolve_editor()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(initial)
        tmp_path = Path(tmp.name)

    try:
        # A non-zero exit (vim's :cq) means abort.
        subprocess.run([*editor, str(tmp_path)], check=True)
        return tmp_path.read_text(encoding="utf-8")
    finally:
        tmp_path.unlink(missing_ok=True)
