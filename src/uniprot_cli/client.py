from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from .cache import ResponseCache, default_response_cache
from .metadata import EndpointDoc, filter_endpoint_docs

DEFAULT_BASE_URL = "https://rest.uniprot.org"
DEFAULT_TIMEOUT_SECONDS = 30.0

ENTRY_DATASETS = {
    "uniprotkb": ("uniprotkb.entry", "accession"),
    "uniref": ("uniref.entry", "id"),
    "uniparc": ("uniparc.entry", "upi"),
    "proteomes": ("proteomes.entry", "upid"),
    "citations": ("support-data.citations.entry", "citationId"),
    "database": ("support-data.database.entry", "id"),
    "diseases": ("support-data.diseases.entry", "id"),
    "keywords": ("support-data.keywords.entry", "id"),
    "locations": ("support-data.locations.entry", "id"),
    "taxonomy": ("support-data.taxonomy.entry", "taxonId"),
    "arba": ("aa.arba.entry", "arbaId"),
    "unirule": ("aa.unirule.entry", "uniruleid"),
}

SEARCH_DATASETS = {
    "uniprotkb": "uniprotkb.search",
    "uniref": "uniref.search",
    "uniparc": "uniparc.search",
    "proteomes": "proteomes.search",
    "genecentric": "proteomes.genecentric-search",
    "citations": "support-data.citations.search",
    "database": "support-data.database.search",
    "diseases": "support-data.diseases.search",
    "keywords": "support-data.keywords.search",
    "locations": "support-data.locations.search",
    "taxonomy": "support-data.taxonomy.search",
    "arba": "aa.arba.search",
    "unirule": "aa.unirule.search",
}

STREAM_DATASETS = {
    "uniprotkb": "uniprotkb.stream",
    "uniref": "uniref.stream",
    "uniparc": "uniparc.stream",
    "proteomes": "proteomes.stream",
    "genecentric": "proteomes.genecentric-stream",
    "citations": "support-data.citations.stream",
    "database": "support-data.database.stream",
    "diseases": "support-data.diseases.stream",
    "keywords": "support-data.keywords.stream",
    "locations": "support-data.locations.stream",
    "taxonomy": "support-data.taxonomy.stream",
    "arba": "aa.arba.stream",
    "unirule": "aa.unirule.stream",
}

IDMAPPING_RESULT_OPERATIONS = {
    "default": ("idmapping.results", "idmapping.results-stream"),
    "uniprotkb": ("idmapping.uniprotkb-results", "idmapping.uniprotkb-results-stream"),
    "uniref": ("idmapping.uniref-results", "idmapping.uniref-results-stream"),
    "uniparc": ("idmapping.uniparc-results", "idmapping.uniparc-results-stream"),
}


QueryParamValue = str | int | float | bool | None


class UniProtCliError(Exception):
    pass


@dataclass(frozen=True)
class UniProtResponse:
    status_code: int
    url: str
    content_type: str
    body: Any
    cached: bool

    def json(self) -> Any:
        if not isinstance(self.body, (dict, list)):
            raise TypeError("response body is not JSON")
        return self.body

    def text(self) -> str:
        if isinstance(self.body, bytes):
            return self.body.decode("utf-8")
        if isinstance(self.body, str):
            return self.body
        return json.dumps(self.body, indent=2, sort_keys=True)


class UniProtClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        cache: ResponseCache | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or base_url_from_env() or DEFAULT_BASE_URL).rstrip("/")
        self.cache = cache or default_response_cache()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> UniProtClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_entry(
        self,
        dataset: str,
        identifier: str,
        *,
        query: Mapping[str, QueryParamValue] | None = None,
        use_cache: bool = True,
        refresh: bool = False,
        decode: str = "auto",
    ) -> UniProtResponse:
        operation_key, path_param = ENTRY_DATASETS[dataset]
        return self.request(
            operation_key,
            path_params={path_param: identifier},
            query_params=dict(query or {}),
            use_cache=use_cache,
            refresh=refresh,
            decode=decode,
        )

    def search(
        self,
        dataset: str,
        query: str,
        *,
        params: Mapping[str, QueryParamValue] | None = None,
        use_cache: bool = True,
        refresh: bool = False,
        decode: str = "auto",
    ) -> UniProtResponse:
        payload: dict[str, QueryParamValue] = {"query": query}
        payload.update(params or {})
        return self.request(
            SEARCH_DATASETS[dataset],
            query_params=payload,
            use_cache=use_cache,
            refresh=refresh,
            decode=decode,
        )

    def stream(
        self,
        dataset: str,
        query: str,
        *,
        params: Mapping[str, QueryParamValue] | None = None,
        use_cache: bool = True,
        refresh: bool = False,
        decode: str = "auto",
    ) -> UniProtResponse:
        payload: dict[str, QueryParamValue] = {"query": query}
        payload.update(params or {})
        return self.request(
            STREAM_DATASETS[dataset],
            query_params=payload,
            use_cache=use_cache,
            refresh=refresh,
            decode=decode,
        )

    def submit_id_mapping(
        self,
        *,
        from_db: str,
        to_db: str,
        ids: Sequence[str],
        use_cache: bool = False,
        refresh: bool = False,
    ) -> UniProtResponse:
        del use_cache, refresh
        response = self._http.post(
            "/idmapping/run",
            data={"from": from_db, "to": to_db, "ids": ",".join(ids)},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(response)
            raise UniProtCliError(
                f"request failed with HTTP {response.status_code}: {response.request.url}{detail}"
            ) from exc
        return _build_response(
            status_code=response.status_code,
            url=str(response.request.url),
            headers=dict(response.headers),
            content=response.content,
            cached=False,
            decode="auto",
        )

    def idmapping_status(self, job_id: str, *, refresh: bool = False) -> UniProtResponse:
        return self.request(
            "idmapping.status",
            path_params={"jobId": job_id},
            refresh=refresh,
        )

    def idmapping_details(self, job_id: str, *, refresh: bool = False) -> UniProtResponse:
        return self.request(
            "idmapping.details",
            path_params={"jobId": job_id},
            refresh=refresh,
        )

    def idmapping_results(
        self,
        job_id: str,
        *,
        result_set: str = "default",
        stream: bool = False,
        query: Mapping[str, QueryParamValue] | None = None,
        use_cache: bool = True,
        refresh: bool = False,
        decode: str = "auto",
    ) -> UniProtResponse:
        search_operation, stream_operation = IDMAPPING_RESULT_OPERATIONS[result_set]
        return self.request(
            stream_operation if stream else search_operation,
            path_params={"jobId": job_id},
            query_params=dict(query or {}),
            use_cache=use_cache,
            refresh=refresh,
            decode=decode,
        )

    def request(
        self,
        operation_key: str,
        *,
        path_params: Mapping[str, str] | None = None,
        query_params: Mapping[str, QueryParamValue] | None = None,
        body: Any = None,
        use_cache: bool = True,
        refresh: bool = False,
        decode: str = "auto",
    ) -> UniProtResponse:
        operation = _resolve_operation(operation_key)
        path = _render_path(operation, path_params or {})
        params = {
            key: value
            for key, value in dict(query_params or {}).items()
            if value is not None
        }
        body_bytes = b"" if body is None else json.dumps(body, sort_keys=True).encode("utf-8")
        cacheable = operation.method == "GET" and use_cache
        cache_key = self.cache.make_key(
            {
                "base_url": self.base_url,
                "operation_key": operation.operation_key,
                "path": path,
                "params": params,
                "body": body,
            }
        )
        if cacheable and not refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return _build_response(
                    status_code=200,
                    url=f"{self.base_url}{path}",
                    headers={"content-type": _preferred_content_type(operation, params)},
                    content=cached,
                    cached=True,
                    decode=decode,
                )
        response = self._http.request(
            operation.method,
            path,
            params=params,
            content=body_bytes or None,
            headers={"content-type": "application/json"} if body is not None else None,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(response)
            raise UniProtCliError(
                f"request failed with HTTP {response.status_code}: {response.request.url}{detail}"
            ) from exc
        if cacheable:
            self.cache.set(cache_key, response.content, ttl_seconds=self.cache_ttl_seconds)
        return _build_response(
            status_code=response.status_code,
            url=str(response.request.url),
            headers=dict(response.headers),
            content=response.content,
            cached=False,
            decode=decode,
        )


def _build_response(
    *,
    status_code: int,
    url: str,
    headers: Mapping[str, str],
    content: bytes,
    cached: bool,
    decode: str,
) -> UniProtResponse:
    content_type = headers.get("content-type", "")
    if decode == "bytes":
        body: Any = content
    elif decode == "text":
        body = content.decode("utf-8")
    elif decode == "json" or "json" in content_type:
        body = json.loads(content.decode("utf-8"))
    elif "text/" in content_type or "xml" in content_type or "rdf" in content_type:
        body = content.decode("utf-8")
    else:
        body = content if decode == "auto" else content.decode("utf-8")
    return UniProtResponse(
        status_code=status_code,
        url=url,
        content_type=content_type,
        body=body,
        cached=cached,
    )


def _preferred_content_type(operation: EndpointDoc, params: Mapping[str, QueryParamValue]) -> str:
    fmt = params.get("format")
    if fmt == "json":
        return "application/json"
    if fmt == "tsv":
        return "text/plain"
    if fmt == "fasta":
        return "text/plain"
    if operation.response_content_types:
        return operation.response_content_types[0]
    return "application/json"


def _render_path(operation: EndpointDoc, path_params: Mapping[str, str]) -> str:
    path = operation.path
    for parameter in operation.path_parameters:
        if parameter.name not in path_params:
            raise UniProtCliError(f"missing required path parameter: {parameter.name}")
        encoded = quote(str(path_params[parameter.name]), safe="")
        path = path.replace("{" + parameter.name + "}", encoded)
    return path


def _resolve_operation(operation_key: str) -> EndpointDoc:
    matches = filter_endpoint_docs(operation_key)
    exact = [item for item in matches if item.operation_key == operation_key]
    if len(exact) == 1:
        return exact[0]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise UniProtCliError(f"unknown operation: {operation_key}")
    raise UniProtCliError(f"ambiguous operation selector: {operation_key}")


def _extract_error_detail(response: httpx.Response) -> str:
    body = response.text.strip()
    if not body:
        return ""
    try:
        parsed = response.json()
    except ValueError:
        return f": {body}"
    if isinstance(parsed, dict):
        for key in ("messages", "message", "error", "detail", "title"):
            value = parsed.get(key)
            if isinstance(value, list) and value:
                return f": {value[0]}"
            if isinstance(value, str) and value:
                return f": {value}"
    return f": {parsed}"


def base_url_from_env() -> str | None:
    return os.environ.get("UNIPROT_API_BASE_URL")
