# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Tests for credential resolution and config paths."""

from __future__ import annotations

import json
import stat

import pytest

from gdoc_vim import auth
from gdoc_vim.onboarding import MissingClientSecretsError

CLIENT = {"installed": {"client_id": "test-client", "client_secret": "s"}}


def _write_client(path, client_id="test-client"):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"installed": {"client_id": client_id, "client_secret": "s"}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_config_dir_honours_env_var(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DEFAULT_CONFIG_DIR", tmp_path / "custom")
    assert auth.token_path() == tmp_path / "custom" / "token.json"
    assert auth.user_credentials_path() == tmp_path / "custom" / "credentials.json"


def test_config_dir_is_private(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DEFAULT_CONFIG_DIR", tmp_path / "cfg")
    created = auth.token_path().parent
    assert stat.S_IMODE(created.stat().st_mode) == 0o700


def test_env_var_client_wins(tmp_path, monkeypatch):
    env_client = tmp_path / "env.json"
    _write_client(env_client, "from-env")
    _write_client(auth.user_credentials_path(), "from-user-file")
    monkeypatch.setenv("GDOC_VIM_CLIENT_SECRETS", str(env_client))

    config = auth._load_client_config()
    assert config["installed"]["client_id"] == "from-env"


def test_user_file_used_when_no_env_var():
    _write_client(auth.user_credentials_path(), "from-user-file")
    config = auth._load_client_config()
    assert config["installed"]["client_id"] == "from-user-file"


def test_missing_client_raises_with_expected_path():
    with pytest.raises(MissingClientSecretsError) as exc:
        auth._load_client_config()
    assert exc.value.dest == auth.user_credentials_path()


def test_no_cached_credentials_when_token_absent():
    assert auth._load_cached_credentials() is None


def test_saved_token_is_private(monkeypatch):
    class FakeCreds:
        def to_json(self):
            return json.dumps({"token": "x"})

    auth._save_credentials(FakeCreds())
    assert stat.S_IMODE(auth.token_path().stat().st_mode) == 0o600


def test_non_interactive_refuses_browser_flow():
    with pytest.raises(RuntimeError, match="non-interactively"):
        auth.get_credentials(interactive=False)
