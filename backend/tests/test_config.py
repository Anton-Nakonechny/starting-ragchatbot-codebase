"""Tests for environment loading in config.

Regression guard: secrets live in a separate ``.env.key`` file (split out from
``.env``). ``load_environment`` must load *both* so ``ANTHROPIC_API_KEY`` is
available at runtime — otherwise the Anthropic client gets an empty key and
every query 500s.
"""

import os


def test_load_environment_reads_api_key_from_env_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".env.key").write_text("ANTHROPIC_API_KEY=secret-from-env-key\n")
    monkeypatch.chdir(tmp_path)

    from config import load_environment

    load_environment()

    assert os.environ["ANTHROPIC_API_KEY"] == "secret-from-env-key"
