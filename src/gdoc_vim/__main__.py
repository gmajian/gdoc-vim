# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Allow running the package with ``python -m gdoc_vim``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
