# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Albert Ma

"""Tests for signing in from a machine with no browser (ssh, headless Linux)."""

from __future__ import annotations

import json

import pytest

from gdoc_vim import auth

BROWSER_ENV = ("SSH_CONNECTION", "SSH_TTY", "DISPLAY")
REDIRECT = "http://localhost:8080/?state=xyz&code=4/0AX4abc-DEF&scope=drive"


@pytest.fixture
def clean_env(monkeypatch):
    for var in BROWSER_ENV:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


# --- detecting a machine without a browser --------------------------------


def test_ssh_connection_is_headless(clean_env):
    clean_env.setenv("SSH_CONNECTION", "10.0.0.1 22 10.0.0.2 22")
    assert auth.is_headless()


def test_ssh_tty_is_headless(clean_env):
    clean_env.setenv("SSH_TTY", "/dev/pts/0")
    assert auth.is_headless()


def test_linux_without_display_is_headless(clean_env, monkeypatch):
    monkeypatch.setattr(auth.sys, "platform", "linux")
    assert auth.is_headless()


def test_linux_with_display_is_not_headless(clean_env, monkeypatch):
    monkeypatch.setattr(auth.sys, "platform", "linux")
    clean_env.setenv("DISPLAY", ":0")
    assert not auth.is_headless()


def test_macos_without_display_is_not_headless(clean_env, monkeypatch):
    monkeypatch.setattr(auth.sys, "platform", "darwin")
    assert not auth.is_headless()


# --- pulling the code out of whatever the user pastes ---------------------


def test_extract_code_from_redirect_url():
    assert auth.extract_code(REDIRECT) == "4/0AX4abc-DEF"


def test_extract_code_accepts_bare_code():
    assert auth.extract_code("  4/0AX4abc-DEF  ") == "4/0AX4abc-DEF"


def test_extract_code_reports_google_errors():
    url = "http://localhost:8080/?error=access_denied"
    with pytest.raises(RuntimeError, match="access_denied"):
        auth.extract_code(url)


def test_extract_code_rejects_url_without_code():
    with pytest.raises(RuntimeError, match="no \\?code="):
        auth.extract_code("http://localhost:8080/")


def test_extract_code_rejects_empty_input():
    with pytest.raises(RuntimeError, match="Nothing pasted"):
        auth.extract_code("   ")


def test_instructions_warn_about_the_dead_page():
    text = auth._headless_instructions("https://accounts.google.com/o/x", 8080)
    assert "can't be reached" in text
    assert "https://accounts.google.com/o/x" in text


# --- the headless flow end to end (with a fake OAuth flow) ----------------


class _FakeFlow:
    """Records how the flow was driven, standing in for InstalledAppFlow."""

    instance: "_FakeFlow | None" = None

    def __init__(self):
        self.redirect_uri = None
        self.fetched_code = None
        self.local_server_kwargs = None
        self.credentials = _FakeCreds()

    @classmethod
    def from_client_config(cls, config, scopes):
        cls.instance = cls()
        return cls.instance

    def authorization_url(self, **kwargs):
        return "https://accounts.google.com/o/oauth2/auth?fake=1", "state"

    def fetch_token(self, code=None, **kwargs):
        self.fetched_code = code

    def run_local_server(self, **kwargs):
        self.local_server_kwargs = kwargs
        return self.credentials


class _FakeCreds:
    def to_json(self):
        return json.dumps({"token": "fake"})


@pytest.fixture
def flow(monkeypatch):
    monkeypatch.setattr(auth, "InstalledAppFlow", _FakeFlow)
    monkeypatch.setattr(auth, "_load_client_config", lambda: {"installed": {}})
    _FakeFlow.instance = None
    return _FakeFlow


def test_headless_exchanges_the_pasted_code(flow, clean_env, monkeypatch):
    clean_env.setenv("SSH_CONNECTION", "x")
    monkeypatch.setattr("builtins.input", lambda _: REDIRECT)

    auth.get_credentials()

    assert flow.instance.fetched_code == "4/0AX4abc-DEF"
    assert flow.instance.redirect_uri == "http://localhost:8080/"
    # No local server may be started; the port is unreachable from outside.
    assert flow.instance.local_server_kwargs is None
    assert auth.token_path().exists()


def test_headless_respects_explicit_port(flow, clean_env, monkeypatch):
    clean_env.setenv("SSH_CONNECTION", "x")
    monkeypatch.setattr("builtins.input", lambda _: REDIRECT)

    auth.get_credentials(port=9999)

    assert flow.instance.redirect_uri == "http://localhost:9999/"


def test_no_browser_flag_forces_paste_flow_on_desktop(flow, clean_env, monkeypatch):
    monkeypatch.setattr(auth.sys, "platform", "darwin")
    monkeypatch.setattr("builtins.input", lambda _: REDIRECT)

    auth.get_credentials(no_browser=True)

    assert flow.instance.fetched_code == "4/0AX4abc-DEF"


def test_desktop_still_uses_the_local_server(flow, clean_env, monkeypatch):
    monkeypatch.setattr(auth.sys, "platform", "darwin")

    auth.get_credentials()

    assert flow.instance.local_server_kwargs == {"port": 0}
    assert flow.instance.fetched_code is None


def test_bad_paste_aborts_without_saving_a_token(flow, clean_env, monkeypatch):
    clean_env.setenv("SSH_CONNECTION", "x")
    monkeypatch.setattr("builtins.input", lambda _: "http://localhost:8080/")

    with pytest.raises(RuntimeError):
        auth.get_credentials()
    assert not auth.token_path().exists()
