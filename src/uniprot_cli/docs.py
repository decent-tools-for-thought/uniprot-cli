from __future__ import annotations

import json
from typing import Any

from .metadata import (
    COLLECTION_SEMANTICS,
    OBSERVED_ON,
    collection_summary,
    filter_endpoint_docs,
    relationship_notes,
)
from .surface import SPECIALIZED_SHORTCUTS, TOP_LEVEL_COMMANDS


def render_docs(selector: str, output_format: str) -> str:
    payload = _docs_payload(selector)
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True)
    return _render_markdown(payload)


def _docs_payload(selector: str) -> dict[str, Any]:
    endpoints = filter_endpoint_docs(selector)
    return {
        "kind": "uniprot_cli_docs",
        "observed_on": OBSERVED_ON,
        "selector": selector,
        "collections": collection_summary(),
        "semantic_model": COLLECTION_SEMANTICS,
        "relationship_notes": relationship_notes(),
        "cli_surface": {
            "top_level_commands": list(TOP_LEVEL_COMMANDS),
            "specialized_shortcuts": [
                {
                    "command": item.command_path,
                    "operation_key": item.operation_key,
                    "identifier_name": item.identifier_name,
                    "identifier_metavar": item.identifier_metavar,
                    "summary": item.summary,
                }
                for item in SPECIALIZED_SHORTCUTS
            ],
        },
        "endpoints": [item.to_dict() for item in endpoints],
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# UniProt CLI Documentation",
        "",
        f"- observed_on: {payload['observed_on']}",
        f"- selector: {payload['selector']}",
        f"- endpoint_count: {len(payload['endpoints'])}",
        "",
        "## CLI Surface",
        "",
    ]
    for command in payload["cli_surface"]["top_level_commands"]:
        lines.extend(
            [
                f"### {command['command']}",
                "",
                f"- summary: {command['summary']}",
            ]
        )
        if "datasets" in command:
            lines.append("- datasets:")
            for dataset in command["datasets"]:
                if "identifier" in dataset:
                    lines.append(
                        f"  - {dataset['dataset']}: operation={dataset['operation_key']}; "
                        f"identifier={dataset['identifier']}"
                    )
                else:
                    lines.append(
                        f"  - {dataset['dataset']}: operation={dataset['operation_key']}"
                    )
        if "subcommands" in command:
            lines.append("- subcommands:")
            for subcommand in command["subcommands"]:
                extra = ""
                if "operation_key" in subcommand:
                    extra = f"; operation={subcommand['operation_key']}"
                if "stream_operation_key" in subcommand:
                    extra += f"; stream_operation={subcommand['stream_operation_key']}"
                lines.append(f"  - {subcommand['name']}{extra}")
        lines.append("")
    lines.extend(
        [
            "### Specialized Shortcuts",
            "",
        ]
    )
    for shortcut in payload["cli_surface"]["specialized_shortcuts"]:
        lines.extend(
            [
                f"- {shortcut['command']}: operation={shortcut['operation_key']}; "
                f"identifier={shortcut['identifier_name']} ({shortcut['identifier_metavar']}); "
                f"summary={shortcut['summary']}",
            ]
        )
    lines.extend(
        [
            "",
        "## Collections",
        "",
        ]
    )
    for collection in payload["collections"]:
        lines.extend(
            [
                f"### {collection['name']}",
                "",
                f"- source_url: {collection['source_url']}",
                f"- semantic_scope: {collection['semantic_scope']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Relationships",
            "",
        ]
    )
    for note in payload["relationship_notes"].values():
        lines.extend(
            [
                f"### {note['topic']}",
                "",
                f"- summary: {note['summary']}",
                f"- uniprotkb: {note['uniprotkb']}",
                f"- uniparc: {note['uniparc']}",
                f"- relationship: {note['relationship']}",
                f"- when_to_use_uniprotkb: {note['when_to_use_uniprotkb']}",
                f"- when_to_use_uniparc: {note['when_to_use_uniparc']}",
                "",
            ]
        )
    for endpoint in payload["endpoints"]:
        lines.extend(
            [
                f"## Endpoint: {endpoint['operation_key']}",
                "",
                f"- method: {endpoint['method']}",
                f"- path: {endpoint['path']}",
                f"- collection: {endpoint['spec_name']}",
                f"- tag: {endpoint['tag']}",
                f"- semantic_kind: {endpoint['semantic_kind']}",
                f"- semantic_summary: {endpoint['semantic_summary']}",
                f"- summary: {endpoint['summary']}",
                f"- description: {endpoint['description']}",
                f"- source_url: {endpoint['source_url']}",
                "",
                "### Parameters",
                "",
            ]
        )
        if endpoint["path_parameters"]:
            lines.append("Path parameters:")
            for parameter in endpoint["path_parameters"]:
                lines.append(
                    f"- {parameter['name']}: required={str(parameter['required']).lower()}; "
                    f"type={parameter['schema_type']}; description={parameter['description']}"
                )
        else:
            lines.append("Path parameters: none")
        if endpoint["query_parameters"]:
            lines.append("")
            lines.append("Query parameters:")
            for parameter in endpoint["query_parameters"]:
                lines.append(
                    f"- {parameter['name']}: required={str(parameter['required']).lower()}; "
                    f"type={parameter['schema_type']}; description={parameter['description']}"
                )
        else:
            lines.append("")
            lines.append("Query parameters: none")
        lines.extend(
            [
                "",
                "### Payloads",
                "",
                (
                    "- request_body: "
                    f"required={str(endpoint['request_body_required']).lower()}; "
                    f"content_types={', '.join(endpoint['request_body_content_types']) or 'none'}"
                ),
                (
                    "- response_content_types: "
                    f"{', '.join(endpoint['response_content_types']) or 'unknown'}"
                ),
                f"- json_schema_ref: {endpoint['json_schema_ref'] or 'none'}",
                "",
            ]
        )
    return "\n".join(lines)
