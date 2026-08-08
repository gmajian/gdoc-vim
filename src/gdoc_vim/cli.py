# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Command-line interface."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from . import __version__
from .auth import build_drive_service
from .drive import (
    HttpError,
    create_doc,
    doc_url,
    export_markdown,
    extract_file_id,
    get_doc_metadata,
    rename_doc,
    update_markdown,
)
from .editor import edit_text
from .onboarding import MissingClientSecretsError, setup_guide


def _eprint(*args) -> None:
    print(*args, file=sys.stderr)


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _edit_and_push(service, file_id: str, *, confirm: bool) -> int:
    """Export, edit locally, push back."""
    original = export_markdown(service, file_id)
    edited = edit_text(original)

    if edited == original:
        _eprint(f"No changes. {doc_url(file_id)}")
        return 0

    if confirm:
        diff = difflib.unified_diff(
            original.splitlines(),
            edited.splitlines(),
            fromfile="remote",
            tofile="edited",
            lineterm="",
        )
        _eprint("\n".join(diff))
        if not _confirm("Push these changes? [y/N] "):
            _eprint("Aborted; document unchanged.")
            return 1

    update_markdown(service, file_id, edited)
    _eprint(f"Pushed. {doc_url(file_id)}")
    return 0


def run(args: argparse.Namespace) -> int:
    service = build_drive_service(force=args.reauth)

    if args.new:
        file_id = create_doc(service, args.new)
        _eprint(f"Created {args.new!r}: {doc_url(file_id)}")
    else:
        file_id = extract_file_id(args.doc)

    if args.title:
        rename_doc(service, file_id, args.title)
        _eprint(f"Renamed to {args.title!r}")
        # Renaming stands on its own unless another action was requested.
        if not (args.output or args.push or args.edit):
            return 0

    if args.output:
        Path(args.output).write_text(export_markdown(service, file_id), "utf-8")
        _eprint(f"Exported -> {args.output}")
        return 0

    if args.push:
        src = Path(args.push)
        if not src.exists():
            _eprint(f"File not found: {src}")
            return 1
        if args.confirm and not _confirm(f"Overwrite document with {src}? [y/N] "):
            _eprint("Aborted; document unchanged.")
            return 1
        update_markdown(service, file_id, src.read_text("utf-8"))
        _eprint(f"Pushed {src} -> {doc_url(file_id)}")
        return 0

    meta = get_doc_metadata(service, file_id)
    _eprint(f"Editing: {meta.get('name')!r}")
    return _edit_and_push(service, file_id, confirm=args.confirm)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gdoc-vim",
        description="Edit Google Docs as Markdown in your terminal editor.",
    )
    p.add_argument("doc", nargs="?", help="Google Doc URL or id.")
    p.add_argument("-n", "--new", metavar="TITLE", help="Create a new doc, then edit.")
    p.add_argument("-t", "--title", metavar="TITLE", help="Rename the doc.")
    p.add_argument("-e", "--edit", action="store_true",
                   help="Open the editor as well (use with -t).")
    p.add_argument("-o", "--output", metavar="FILE", help="Export to FILE; no editor.")
    p.add_argument("-p", "--push", metavar="FILE", help="Upload FILE; no editor.")
    p.add_argument("-c", "--confirm", action="store_true",
                   help="Show a diff and ask before uploading.")
    p.add_argument("--reauth", action="store_true", help="Re-run browser sign-in.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.doc and not args.new:
        parser.error("provide a Google Doc URL/id, or -n TITLE to create one.")
    if args.doc and args.new:
        parser.error("give either a doc URL or -n TITLE, not both.")
    if args.new and args.title:
        parser.error("-n already sets the title; -t is redundant.")

    if args.output and args.push:
        parser.error("-o and -p are mutually exclusive.")

    try:
        return run(args)
    except MissingClientSecretsError as e:
        _eprint(setup_guide(e.dest))
        return 1
    except HttpError as e:
        _eprint(f"Google API error: {e}")
        return 1
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        _eprint(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        _eprint("\nInterrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
