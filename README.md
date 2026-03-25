<div align="center">

# uniprot-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/uniprot-cli?sort=semver&color=0f766e)](https://github.com/decent-tools-for-thought/uniprot-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-0ea5e9)
![License](https://img.shields.io/badge/license-0BSD-14b8a6)

Command-line client for UniProt entry lookup, paginated and streamed search, asynchronous ID mapping, direct operation calls, offline docs, and optional local caching.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Configuration](#configuration)
- [Config File](#config-file)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install
$$\color{#0EA5E9}Install \space \color{#14B8A6}Tool$$

```bash
uv tool install .      # install the CLI
uniprot-cli --help     # inspect the command surface
```

## Functionality
$$\color{#0EA5E9}Record \space \color{#14B8A6}Lookup$$
- `uniprot-cli get-entry <dataset> <identifier>`: fetch one UniProt record by identifier.
- `uniprot-cli search <dataset> <query>`: run a paginated search against one supported dataset.
- `uniprot-cli stream <dataset> <query>`: run a streamed bulk query for datasets that support streaming.
- `uniprot-cli search|stream --query-param NAME=VALUE`: pass native query parameters directly to the upstream API.

$$\color{#0EA5E9}ID \space \color{#14B8A6}Mapping$$
- `uniprot-cli idmapping run --from <db> --to <db> <id>...`: submit an asynchronous ID mapping job.
- `uniprot-cli idmapping status <job-id>`: poll mapping job status.
- `uniprot-cli idmapping details <job-id>`: inspect mapping job metadata.
- `uniprot-cli idmapping results <job-id>`: fetch the completed result set, optionally with `--target` and `--stream`.

$$\color{#0EA5E9}Direct \space \color{#14B8A6}Calls$$
- `uniprot-cli request <operation>`: call any shipped OpenAPI operation directly by operation key.
- `uniprot-cli request --path NAME=VALUE --query NAME=VALUE --body-json ...`: fill path parameters, query parameters, and request bodies explicitly.
- `uniprot-cli docs [selector]`: print LLM-oriented documentation for the bundled UniProt operations.
- `uniprot-cli docs --format markdown|json`: emit either Markdown or machine-readable JSON.

$$\color{#0EA5E9}Output \space \color{#14B8A6}Control$$
- `uniprot-cli --decode auto|json|text|bytes`: choose response decoding behavior for entry, search, stream, request, and ID mapping result commands.
- The client ships a generic wrapper over the published UniProt OpenAPI specs and caches GET requests on disk.

$$\color{#0EA5E9}Cache \space \color{#14B8A6}Control$$
- `uniprot-cli cache stats`: show cache size and entry counts.
- `uniprot-cli cache prune --max-size-gb <n>`: evict older cache entries until the cache fits the target cap.
- `uniprot-cli cache clear`: remove all cached responses.

## Configuration
$$\color{#0EA5E9}Tune \space \color{#14B8A6}Defaults$$

By default the CLI targets the published UniProt REST services, leaves GET-response caching disabled, and auto-decodes responses based on content type.

- Use `--base-url` to point at another UniProt-compatible endpoint.
- Use `--decode json|text|bytes` when you want to override automatic response decoding.
- Use `--max-cache-size-gb` with a value greater than `0` to enable local caching for GET requests.
- Use `--no-cache` or `--refresh` when you want live responses instead of cached ones.

The main environment variables are `UNIPROT_API_BASE_URL`, `UNIPROT_CACHE_DIR`, `UNIPROT_CACHE_MAX_BYTES`, and `XDG_CACHE_HOME`.

## Config File
$$\color{#0EA5E9}Set \space \color{#14B8A6}Defaults$$

The CLI reads optional defaults from `$XDG_CONFIG_HOME/uniprot-cli/config.toml`, falling back to `~/.config/uniprot-cli/config.toml`.

Start from `config/default-config.toml` in this repo. The shipped default keeps caching off:

```toml
[cache]
max_size_gb = 0.0
```

## Quick Start
$$\color{#0EA5E9}Try \space \color{#14B8A6}Browse$$

```bash
uniprot-cli get-entry uniprotkb P05067                                      # fetch one UniProtKB record
uniprot-cli search uniprotkb "gene:APP AND organism_id:9606" --query-param size=1
uniprot-cli stream taxonomy "scientific_name:Homo sapiens" --query-param format=json
uniprot-cli idmapping run --from UniProtKB_AC-ID --to GeneID P05067 Q9Y261  # submit a mapping job
uniprot-cli request uniprotkb.entry --path accession=P05067 --query format=json
uniprot-cli docs idmapping --format json                                    # inspect bundled docs
```

## Credits

This client is built for the UniProt REST API and is not affiliated with UniProt.

Credit goes to the UniProt Consortium for the protein knowledgebase, identifier mapping services, OpenAPI descriptions, and endpoint documentation this tool builds on.
