import json
from algoxray.cli import main
import pytest


def test_cli_registry_is_readable(capsys):
    assert main(["list"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert any(f["id"] == "dijkstra_correct" for f in result)


def test_cli_local_execution_requires_explicit_trust_flag(tmp_path):
    p = tmp_path / "not_loaded.py"
    p.write_text("raise AssertionError('must not execute')", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["analyze", "--problem", "dijkstra_v1", "--submission", str(p)])
    assert exc.value.code == 2
