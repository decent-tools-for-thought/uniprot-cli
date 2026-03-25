from __future__ import annotations

from pathlib import Path

import httpx

from uniprot_cli.cache import DiskLRUCache
from uniprot_cli.client import UniProtClient


def test_get_entry_renders_path_and_parses_json(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/uniprotkb/P05067"
        assert request.url.params["format"] == "json"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"primaryAccession": "P05067"},
        )

    transport = httpx.MockTransport(handler)
    cache = DiskLRUCache(root=tmp_path / "cache")
    with UniProtClient(transport=transport, cache=cache) as client:
        response = client.get_entry("uniprotkb", "P05067", query={"format": "json"})

    assert response.json()["primaryAccession"] == "P05067"


def test_submit_id_mapping_posts_json_body(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/idmapping/run"
        assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
        assert request.content.decode("utf-8") == "from=UniProtKB_AC-ID&to=GeneID&ids=P05067"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jobId": "job-123"},
        )

    transport = httpx.MockTransport(handler)
    cache = DiskLRUCache(root=tmp_path / "cache")
    with UniProtClient(transport=transport, cache=cache) as client:
        response = client.submit_id_mapping(
            from_db="UniProtKB_AC-ID",
            to_db="GeneID",
            ids=["P05067"],
        )

    assert response.json()["jobId"] == "job-123"
