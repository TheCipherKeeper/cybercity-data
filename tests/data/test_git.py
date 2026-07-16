"""Git changes gateway tests."""

import subprocess
from pathlib import Path

from cybercity_data.city_model.adapters.inbound.data.git import GitChangesGateway


def test_previous_network_json_returns_stdout(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_run(*args, **kwargs):
        class Result:
            stdout = '{"version":"3.0.0"}'
            stderr = ""

        calls.append((args, kwargs))
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    gateway = GitChangesGateway(tmp_path)
    assert gateway.previous_network_json() == '{"version":"3.0.0"}'
    assert calls[0][0][0] == ["git", "show", "HEAD:build/network.json"]


def test_previous_network_json_returns_none_on_failure(tmp_path: Path, monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(subprocess, "run", fake_run)
    gateway = GitChangesGateway(tmp_path)
    assert gateway.previous_network_json() is None


def test_head_ref_returns_sha(tmp_path: Path, monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        class Result:
            stdout = "abc123\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    gateway = GitChangesGateway(tmp_path)
    assert gateway.head_ref() == "abc123"


def test_head_timestamp_returns_iso(tmp_path: Path, monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        class Result:
            stdout = "2024-01-01T00:00:00+00:00\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    gateway = GitChangesGateway(tmp_path)
    assert gateway.head_timestamp() == "2024-01-01T00:00:00+00:00"
