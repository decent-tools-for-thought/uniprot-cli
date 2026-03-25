from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

OBSERVED_ON = "2026-03-24"
SPEC_SOURCES = {
    "uniprotkb": "https://rest.uniprot.org/uniprotkb/api/docs",
    "uniref": "https://rest.uniprot.org/uniref/api/docs",
    "uniparc": "https://rest.uniprot.org/uniparc/api/docs",
    "proteomes": "https://rest.uniprot.org/proteomes/api/docs",
    "support-data": "https://rest.uniprot.org/support-data/api/docs",
    "aa": "https://rest.uniprot.org/aa/api/docs",
    "idmapping": "https://rest.uniprot.org/idmapping/api/docs",
}

COLLECTION_SEMANTICS = {
    "uniprotkb": (
        "Curated protein records in the UniProt Knowledgebase. These are the canonical protein-"
        "centric entries most users want for sequence, annotation, function, features, and cross-"
        "references. UniProtKB is where biological meaning is attached to proteins."
    ),
    "uniref": (
        "Sequence clusters that reduce redundancy. These endpoints answer questions about cluster "
        "representatives and cluster membership rather than about a single curated protein record."
    ),
    "uniparc": (
        "The sequence archive. UniParc is about distinct protein sequences and their database "
        "history across sources, not about expert functional annotation. UniParc is where sequence "
        "identity and source provenance are tracked independently of curation."
    ),
    "proteomes": (
        "Proteome-level resources, including proteome metadata and gene-centric protein views that "
        "group products within a proteome context."
    ),
    "support-data": (
        "Controlled vocabularies and reference data such as taxonomy, diseases, keywords, "
        "subcellular locations, literature citations, and external databases."
    ),
    "aa": (
        "Automatic annotation rule systems. ARBA and UniRule describe reusable annotation rules "
        "applied across proteins rather than protein entries themselves."
    ),
    "idmapping": (
        "Asynchronous identifier translation jobs. This surface is about submitting jobs, polling "
        "their state, and retrieving mapped results in different target representations."
    ),
}

RELATIONSHIP_NOTES = {
    "uniprotkb_vs_uniparc": {
        "topic": "UniProtKB versus UniParc",
        "summary": (
            "UniProtKB is the curated protein knowledgebase; UniParc is the non-redundant sequence "
            "archive. If you want biological interpretation of a protein, start with UniProtKB. If "
            "you want to know whether an exact sequence has appeared before and in which source "
            "databases, pivot to UniParc."
        ),
        "uniprotkb": (
            "Protein-entry view. Records carry names, function, features, evidence, literature, "
            "taxonomy, and rich cross-references. Multiple UniProtKB records can refer to "
            "sequences that are related, and isoforms/annotation context matter."
        ),
        "uniparc": (
            "Sequence-identity view. Records represent a unique sequence plus its source-database "
            "history and cross-references. UniParc does not try to be the main home of functional "
            "annotation."
        ),
        "relationship": (
            "UniProtKB entries are one important source that feed into UniParc. UniParc "
            "deduplicates exact sequences across source databases, while UniProtKB curates "
            "protein-centric knowledge on top of specific entries."
        ),
        "when_to_use_uniprotkb": (
            "Use UniProtKB when you have an accession or protein query and want biology: names, "
            "function, domains, PTMs, subcellular location, disease links, evidence, and "
            "references."
        ),
        "when_to_use_uniparc": (
            "Use UniParc when you care about exact sequence identity, archive history, or need to "
            "trace where the same sequence appears across databases and proteomes."
        ),
    }
}


@dataclass(frozen=True)
class ParameterDoc:
    name: str
    location: str
    required: bool
    description: str
    schema_type: str | None
    example: str | None


@dataclass(frozen=True)
class EndpointDoc:
    operation_key: str
    spec_name: str
    tag: str
    tag_description: str
    method: str
    path: str
    summary: str
    description: str
    semantic_kind: str
    semantic_summary: str
    path_parameters: tuple[ParameterDoc, ...]
    query_parameters: tuple[ParameterDoc, ...]
    request_body_required: bool
    request_body_content_types: tuple[str, ...]
    response_content_types: tuple[str, ...]
    json_schema_ref: str | None
    source_url: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path_parameters"] = [asdict(item) for item in self.path_parameters]
        payload["query_parameters"] = [asdict(item) for item in self.query_parameters]
        return payload


def available_operation_keys() -> tuple[str, ...]:
    return tuple(item.operation_key for item in endpoint_docs())


def collection_names() -> tuple[str, ...]:
    return tuple(SPEC_SOURCES.keys())


@lru_cache(maxsize=1)
def endpoint_docs() -> tuple[EndpointDoc, ...]:
    docs: list[EndpointDoc] = []
    for spec_name, spec in _raw_specs().items():
        tags = {
            item["name"]: _clean_text(item.get("description", ""))
            for item in spec.get("tags", [])
        }
        for path, path_item in spec["paths"].items():
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post"}:
                    continue
                tag = operation["tags"][0]
                parameters = [
                    _parameter_doc(item)
                    for item in operation.get("parameters", [])
                ]
                request_body = operation.get("requestBody", {})
                request_content = tuple(sorted(request_body.get("content", {}).keys()))
                response_content = tuple(sorted(_response_content_keys(operation)))
                docs.append(
                    EndpointDoc(
                        operation_key=_operation_key(spec_name, path, method),
                        spec_name=spec_name,
                        tag=tag,
                        tag_description=tags.get(tag, ""),
                        method=method.upper(),
                        path=path,
                        summary=_clean_text(operation.get("summary", "")),
                        description=_clean_text(operation.get("description", "")),
                        semantic_kind=_semantic_kind(path, method),
                        semantic_summary=_semantic_summary(spec_name, path, method),
                        path_parameters=tuple(
                            item for item in parameters if item.location == "path"
                        ),
                        query_parameters=tuple(
                            item for item in parameters if item.location == "query"
                        ),
                        request_body_required=bool(request_body.get("required", False)),
                        request_body_content_types=request_content,
                        response_content_types=response_content,
                        json_schema_ref=_json_schema_ref(operation),
                        source_url=SPEC_SOURCES[spec_name],
                    )
                )
    return tuple(sorted(docs, key=lambda item: (item.spec_name, item.path, item.method)))


def filter_endpoint_docs(selector: str) -> tuple[EndpointDoc, ...]:
    if selector == "all":
        return endpoint_docs()
    if selector in SPEC_SOURCES:
        return tuple(item for item in endpoint_docs() if item.spec_name == selector)
    matches = [
        item
        for item in endpoint_docs()
        if selector == item.operation_key
        or selector == item.spec_name
        or selector == item.path
        or selector in item.operation_key
        or selector in item.path
    ]
    return tuple(matches)


def collection_summary() -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "source_url": SPEC_SOURCES[name],
            "semantic_scope": COLLECTION_SEMANTICS[name],
        }
        for name in SPEC_SOURCES
    ]


def relationship_notes() -> dict[str, dict[str, str]]:
    return RELATIONSHIP_NOTES


def _parameter_doc(item: dict[str, Any]) -> ParameterDoc:
    schema = item.get("schema", {})
    schema_type = schema.get("type")
    if schema_type is None and "$ref" in schema:
        schema_type = schema["$ref"].split("/")[-1]
    example = item.get("example")
    return ParameterDoc(
        name=item["name"],
        location=item["in"],
        required=bool(item.get("required", False)),
        description=_clean_text(item.get("description", "")),
        schema_type=schema_type,
        example=None if example is None else str(example),
    )


def _json_schema_ref(operation: dict[str, Any]) -> str | None:
    content = operation.get("responses", {}).get("default", {}).get("content", {})
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return None
    schema = json_content.get("schema", {})
    if "$ref" in schema:
        return str(schema["$ref"])
    if "items" in schema and isinstance(schema["items"], dict) and "$ref" in schema["items"]:
        return str(schema["items"]["$ref"])
    return None


def _semantic_kind(path: str, method: str) -> str:
    if method.lower() == "post":
        return "job_submission"
    if path.endswith("/search"):
        return "search"
    if path.endswith("/stream"):
        return "stream"
    if "/results/stream/" in path or path.endswith("/stream/{jobId}"):
        return "job_results_stream"
    if "/results/" in path:
        return "job_results"
    if "/status/" in path:
        return "job_status"
    if "/details/" in path:
        return "job_details"
    if path.endswith("/members"):
        return "member_listing"
    if path.endswith("/members/stream"):
        return "member_stream"
    if path.endswith("/databases"):
        return "cross_reference_listing"
    if path.endswith("/databases/stream"):
        return "cross_reference_stream"
    if path.endswith("/light"):
        return "lightweight_entry"
    return "entry"


def _semantic_summary(spec_name: str, path: str, method: str) -> str:
    kind = _semantic_kind(path, method)
    if kind == "job_submission":
        return "Submit an asynchronous ID mapping job and receive a job identifier."
    if kind == "search":
        return (
            "Run a paginated search over this collection. This is the exploration surface when you "
            "do not know the exact identifier yet."
        )
    if kind == "stream":
        return (
            "Return the entire query result as a single streamed download. Use it when you want a "
            "bulk export rather than page-by-page traversal."
        )
    if kind == "job_results":
        return "Retrieve paginated results for a completed ID mapping job."
    if kind == "job_results_stream":
        return "Stream the full result set for a completed ID mapping job in one response."
    if kind == "job_status":
        return "Poll the lifecycle state of an asynchronous ID mapping job."
    if kind == "job_details":
        return "Inspect job metadata and result links for an asynchronous ID mapping job."
    if kind == "member_listing":
        return "List the members that belong to a UniRef cluster."
    if kind == "member_stream":
        return "Download all members of a UniRef cluster in a single stream."
    if kind == "cross_reference_listing":
        return "List cross-database records associated with a UniParc archive sequence."
    if kind == "cross_reference_stream":
        return "Stream all cross-database records associated with a UniParc archive sequence."
    if kind == "lightweight_entry":
        return "Fetch a reduced projection of an entry for lighter-weight retrieval."
    if spec_name == "support-data":
        return (
            "Retrieve a single controlled vocabulary or reference-data record by its stable "
            "identifier."
        )
    if spec_name == "aa":
        return "Retrieve a single automatic annotation rule by its stable identifier."
    if spec_name == "uniparc" and "/proteome/" in path:
        return (
            "Navigate from a proteome identifier to the UniParc sequences linked "
            "to that proteome."
        )
    if spec_name == "proteomes" and path.startswith("/genecentric"):
        return "Retrieve a gene-centric protein grouping within proteome-level data."
    return "Retrieve a single canonical record by its stable identifier."


def _operation_key(spec_name: str, path: str, method: str) -> str:
    if spec_name == "idmapping":
        if path == "/idmapping/run":
            return "idmapping.run"
        if path == "/idmapping/status/{jobId}":
            return "idmapping.status"
        if path == "/idmapping/details/{jobId}":
            return "idmapping.details"
        if path == "/idmapping/results/{jobId}":
            return "idmapping.results"
        if path == "/idmapping/stream/{jobId}":
            return "idmapping.results-stream"
        parts = path.strip("/").split("/")
        target = parts[1]
        stream_suffix = "-stream" if "stream" in parts else ""
        return f"idmapping.{target}-results{stream_suffix}"
    if spec_name == "proteomes" and path.startswith("/genecentric/"):
        if path == "/genecentric/search":
            return "proteomes.genecentric-search"
        if path == "/genecentric/stream":
            return "proteomes.genecentric-stream"
        if path == "/genecentric/{accession}":
            return "proteomes.genecentric-entry"
        if path == "/genecentric/upid/{upid}":
            return "proteomes.genecentric-upid-entry"
    if spec_name in {"support-data", "aa"}:
        resource = path.strip("/").split("/")[0]
        return f"{spec_name}.{resource}.{_path_action(path, method)}"
    return f"{spec_name}.{_path_action(path, method)}"


def _path_action(path: str, method: str) -> str:
    if method.lower() == "post":
        return "submit"
    if path.endswith("/members/stream"):
        return "members-stream"
    if path.endswith("/members"):
        return "members"
    if path.endswith("/databases/stream"):
        return "databases-stream"
    if path.endswith("/databases"):
        return "databases"
    if "/proteome/" in path and path.endswith("/stream"):
        return "proteome-stream"
    if "/proteome/" in path:
        return "proteome"
    if path.endswith("/search"):
        return "search"
    if path.endswith("/stream"):
        return "stream"
    if path.endswith("/light"):
        return "light"
    if path.startswith("/genecentric/upid/"):
        return "upid-entry"
    if path.startswith("/genecentric/"):
        return "entry"
    if "{" in path:
        return "entry"
    return "request"


def _raw_specs() -> dict[str, dict[str, Any]]:
    root = files("uniprot_cli").joinpath("specs")
    return {
        spec_name: json.loads(root.joinpath(f"{spec_name}.openapi.json").read_text())
        for spec_name in SPEC_SOURCES
    }


def _response_content_keys(operation: dict[str, Any]) -> list[str]:
    content = operation.get("responses", {}).get("default", {}).get("content", {})
    return list(content.keys())


def _clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value)
    collapsed = re.sub(r"\s+", " ", without_tags)
    return collapsed.strip()
