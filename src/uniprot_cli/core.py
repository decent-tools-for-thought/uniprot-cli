from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .cache import CacheSettings, DiskLRUCache, create_response_cache, load_cache_settings
from .client import (
    ENTRY_DATASETS,
    IDMAPPING_RESULT_OPERATIONS,
    SEARCH_DATASETS,
    STREAM_DATASETS,
    UniProtClient,
    UniProtCliError,
)
from .docs import render_docs


def build_parser(cache_settings: CacheSettings | None = None) -> argparse.ArgumentParser:
    settings = load_cache_settings() if cache_settings is None else cache_settings
    parser = argparse.ArgumentParser(prog="uniprot-cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    entry_parser = subparsers.add_parser("get-entry", help="Fetch a single record by identifier")
    entry_parser.add_argument("dataset", choices=sorted(ENTRY_DATASETS))
    entry_parser.add_argument("identifier")
    _add_common_query_args(entry_parser, settings)

    search_parser = subparsers.add_parser("search", help="Run a paginated search")
    search_parser.add_argument("dataset", choices=sorted(SEARCH_DATASETS))
    search_parser.add_argument("query")
    _add_common_query_args(search_parser, settings)

    stream_parser = subparsers.add_parser("stream", help="Run a streamed bulk query")
    stream_parser.add_argument("dataset", choices=sorted(STREAM_DATASETS))
    stream_parser.add_argument("query")
    _add_common_query_args(stream_parser, settings)

    request_parser = subparsers.add_parser("request", help="Call an operation directly by key")
    request_parser.add_argument("operation")
    request_parser.add_argument("--path", action="append", default=[], metavar="NAME=VALUE")
    request_parser.add_argument("--query", action="append", default=[], metavar="NAME=VALUE")
    request_parser.add_argument("--body-json", default=None)
    _add_runtime_args(request_parser, settings)
    request_parser.add_argument(
        "--decode",
        choices=["auto", "json", "text", "bytes"],
        default="auto",
    )

    idmapping_parser = subparsers.add_parser("idmapping", help="Work with asynchronous ID mapping")
    idmapping_subparsers = idmapping_parser.add_subparsers(dest="idmapping_command", required=True)

    idmapping_run = idmapping_subparsers.add_parser("run", help="Submit an ID mapping job")
    idmapping_run.add_argument("--from", dest="from_db", required=True)
    idmapping_run.add_argument("--to", dest="to_db", required=True)
    idmapping_run.add_argument("ids", nargs="+")
    _add_runtime_args(idmapping_run, settings)

    idmapping_status = idmapping_subparsers.add_parser("status", help="Poll a job status")
    idmapping_status.add_argument("job_id")
    _add_runtime_args(idmapping_status, settings)

    idmapping_details = idmapping_subparsers.add_parser("details", help="Inspect job details")
    idmapping_details.add_argument("job_id")
    _add_runtime_args(idmapping_details, settings)

    idmapping_results = idmapping_subparsers.add_parser("results", help="Fetch job results")
    idmapping_results.add_argument("job_id")
    idmapping_results.add_argument(
        "--target",
        choices=sorted(IDMAPPING_RESULT_OPERATIONS),
        default="default",
    )
    idmapping_results.add_argument("--stream", action="store_true")
    _add_common_query_args(idmapping_results, settings)

    docs_parser = subparsers.add_parser(
        "docs",
        help="Show LLM-friendly documentation for UniProt operations",
    )
    docs_parser.add_argument("selector", nargs="?", default="all")
    docs_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["markdown", "json"],
        default="markdown",
    )

    cache_parser = subparsers.add_parser("cache", help="Manage the UniProt response cache")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", required=True)

    cache_stats = cache_subparsers.add_parser("stats", help="Show cache statistics")
    _add_cache_only_args(cache_stats, settings)

    cache_prune = cache_subparsers.add_parser("prune", help="Evict old cache entries")
    _add_cache_only_args(cache_prune, settings)

    cache_clear = cache_subparsers.add_parser("clear", help="Delete all cache entries")
    _add_cache_only_args(cache_clear, settings)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        cache_settings = load_cache_settings()
    except ValueError as error:
        sys.stderr.write(f"error: {error}\n")
        return 2

    parser = build_parser(cache_settings)
    args = parser.parse_args(argv)
    try:
        if args.command == "docs":
            return _run_docs(args)
        if args.command == "cache":
            return _run_cache(args)
        return _run_remote(args)
    except UniProtCliError as error:
        parser.exit(status=2, message=f"error: {error}\n")
    return 0


def _run_remote(args: argparse.Namespace) -> int:
    max_bytes = _gigabytes_to_bytes(args.max_cache_size_gb)
    cache = create_response_cache(root=args.cache_dir, max_bytes=max_bytes)
    with UniProtClient(base_url=args.base_url, cache=cache) as client:
        use_cache = not args.no_cache and max_bytes > 0
        refresh = args.refresh
        decode = getattr(args, "decode", "auto")
        if args.command == "get-entry":
            response = client.get_entry(
                args.dataset,
                args.identifier,
                query=_parse_assignments(args.query_params),
                use_cache=use_cache,
                refresh=refresh,
                decode=decode,
            )
        elif args.command == "search":
            response = client.search(
                args.dataset,
                args.query,
                params=_parse_assignments(args.query_params),
                use_cache=use_cache,
                refresh=refresh,
                decode=decode,
            )
        elif args.command == "stream":
            response = client.stream(
                args.dataset,
                args.query,
                params=_parse_assignments(args.query_params),
                use_cache=use_cache,
                refresh=refresh,
                decode=decode,
            )
        elif args.command == "request":
            response = client.request(
                args.operation,
                path_params=_parse_assignments(args.path),
                query_params=_parse_assignments(args.query),
                body=None if args.body_json is None else json.loads(args.body_json),
                use_cache=use_cache,
                refresh=refresh,
                decode=decode,
            )
        elif args.command == "idmapping":
            if args.idmapping_command == "run":
                response = client.submit_id_mapping(
                    from_db=args.from_db,
                    to_db=args.to_db,
                    ids=args.ids,
                    use_cache=False,
                    refresh=refresh,
                )
            elif args.idmapping_command == "status":
                response = client.idmapping_status(args.job_id, refresh=refresh)
            elif args.idmapping_command == "details":
                response = client.idmapping_details(args.job_id, refresh=refresh)
            elif args.idmapping_command == "results":
                response = client.idmapping_results(
                    args.job_id,
                    result_set=args.target,
                    stream=args.stream,
                    query=_parse_assignments(args.query_params),
                    use_cache=use_cache,
                    refresh=refresh,
                    decode=decode,
                )
            else:
                raise UniProtCliError(f"unsupported idmapping command: {args.idmapping_command}")
        else:
            raise UniProtCliError(f"unsupported command: {args.command}")
    _write_response(response)
    return 0


def _run_cache(args: argparse.Namespace) -> int:
    max_bytes = _gigabytes_to_bytes(args.max_size_gb)
    cache = DiskLRUCache(root=args.cache_dir, max_bytes=max_bytes)
    if args.cache_command == "stats":
        stats = cache.stats()
    elif args.cache_command == "prune":
        stats = cache.prune()
    elif args.cache_command == "clear":
        cache.clear()
        stats = cache.stats()
    else:
        raise UniProtCliError(f"unsupported cache command: {args.cache_command}")
    print(
        json.dumps(
            {
                "cache_dir": str(args.cache_dir),
                "entries": stats.entries,
                "total_bytes": stats.total_bytes,
                "max_bytes": stats.max_bytes,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _run_docs(args: argparse.Namespace) -> int:
    print(render_docs(args.selector, args.output_format), end="")
    if args.output_format != "markdown":
        print()
    return 0


def _add_common_query_args(parser: argparse.ArgumentParser, settings: CacheSettings) -> None:
    parser.add_argument(
        "--query-param",
        dest="query_params",
        action="append",
        default=[],
        metavar="NAME=VALUE",
    )
    _add_runtime_args(parser, settings)
    parser.add_argument(
        "--decode",
        choices=["auto", "json", "text", "bytes"],
        default="auto",
    )


def _add_runtime_args(parser: argparse.ArgumentParser, settings: CacheSettings) -> None:
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--cache-dir", type=Path, default=settings.cache_dir)
    parser.add_argument(
        "--max-cache-size-gb",
        type=float,
        default=settings.max_size_gb,
    )
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--refresh", action="store_true")


def _add_cache_only_args(parser: argparse.ArgumentParser, settings: CacheSettings) -> None:
    parser.add_argument("--cache-dir", type=Path, default=settings.cache_dir)
    parser.add_argument(
        "--max-size-gb",
        type=float,
        default=settings.max_size_gb,
    )


def _parse_assignments(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise UniProtCliError(f"expected NAME=VALUE, got: {value}")
        key, raw = value.split("=", 1)
        parsed[key] = raw
    return parsed


def _write_response(response: Any) -> None:
    body = response.body
    if isinstance(body, bytes):
        sys.stdout.buffer.write(body)
        return
    if isinstance(body, str):
        print(body)
        return
    print(json.dumps(body, indent=2, sort_keys=True))


def _gigabytes_to_bytes(size_gb: float) -> int:
    if size_gb < 0:
        raise UniProtCliError("cache size must be non-negative")
    return int(size_gb * 1024**3)
