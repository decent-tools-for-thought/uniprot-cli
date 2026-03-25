from __future__ import annotations

import json

from uniprot_cli.docs import render_docs


def test_render_docs_json_for_single_collection() -> None:
    payload = json.loads(render_docs("uniprotkb", "json"))

    assert payload["kind"] == "uniprot_cli_docs"
    assert payload["observed_on"] == "2026-03-24"
    assert payload["selector"] == "uniprotkb"
    assert payload["cli_surface"]["top_level_commands"][0]["command"] == "get-entry"
    assert any(
        item["command"] == "uniref members"
        for item in payload["cli_surface"]["specialized_shortcuts"]
    )
    assert len(payload["endpoints"]) == 3
    assert payload["endpoints"][0]["spec_name"] == "uniprotkb"
    assert "uniprotkb_vs_uniparc" in payload["relationship_notes"]
    assert (
        "curated protein knowledgebase"
        in payload["relationship_notes"]["uniprotkb_vs_uniparc"]["summary"]
    )


def test_render_docs_markdown_contains_semantic_sections() -> None:
    rendered = render_docs("idmapping", "markdown")

    assert "# UniProt CLI Documentation" in rendered
    assert "## CLI Surface" in rendered
    assert "### Specialized Shortcuts" in rendered
    assert "## Relationships" in rendered
    assert "### UniProtKB versus UniParc" in rendered
    assert "## Endpoint: idmapping.run" in rendered
    assert "- semantic_kind: job_submission" in rendered
    assert "Retrieve paginated results for a completed ID mapping job." in rendered
