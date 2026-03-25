from __future__ import annotations

from uniprot_cli.core import build_parser


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
