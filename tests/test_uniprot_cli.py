from __future__ import annotations

import json
from pathlib import Path

import pytest

from uniprot_cli.core import build_parser, main


def test_cli_parses_docs_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["docs", "uniprotkb", "--format", "json"])

    assert args.command == "docs"
    assert args.selector == "uniprotkb"
    assert args.output_format == "json"


def test_cli_parses_generic_request() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "request",
            "uniprotkb.entry",
            "--path",
            "accession=P05067",
            "--query",
            "format=json",
        ]
    )

    assert args.command == "request"
    assert args.operation == "uniprotkb.entry"
    assert args.path == ["accession=P05067"]
    assert args.query == ["format=json"]


def test_parser_reads_cache_defaults_from_xdg_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "uniprot-cli" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '[cache]\nmax_size_gb = 0.25\ndir = "/tmp/uniprot-cache"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    args = build_parser().parse_args(["docs"])

    assert args.command == "docs"
    remote_args = build_parser().parse_args(["get-entry", "uniprotkb", "P05067"])
    assert remote_args.max_cache_size_gb == 0.25
    assert remote_args.cache_dir == Path("/tmp/uniprot-cache")


def test_main_skips_disk_cache_when_default_cache_is_disabled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class StubClient:
        def __enter__(self) -> StubClient:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def get_entry(self, *_: object, **__: object) -> object:
            return type("Response", (), {"body": {"accession": "P05067"}})()

    def fail_disk_cache(*_: object, **__: object) -> object:
        raise AssertionError("DiskLRUCache should not be created when cache is disabled")

    monkeypatch.setattr("uniprot_cli.core.UniProtClient", lambda **_: StubClient())
    monkeypatch.setattr("uniprot_cli.core.DiskLRUCache", fail_disk_cache)

    code = main(["get-entry", "uniprotkb", "P05067"])

    assert code == 0
    assert json.loads(capsys.readouterr().out) == {"accession": "P05067"}
