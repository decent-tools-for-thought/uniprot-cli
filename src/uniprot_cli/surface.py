from __future__ import annotations

from dataclasses import dataclass

from .client import ENTRY_DATASETS, IDMAPPING_RESULT_OPERATIONS, SEARCH_DATASETS, STREAM_DATASETS


@dataclass(frozen=True)
class ShortcutCommand:
    group: str
    name: str
    operation_key: str
    identifier_name: str
    identifier_metavar: str
    help: str
    summary: str

    @property
    def command_path(self) -> str:
        return f"{self.group} {self.name}"


SPECIALIZED_SHORTCUTS = (
    ShortcutCommand(
        group="uniref",
        name="light",
        operation_key="uniref.light",
        identifier_name="id",
        identifier_metavar="ID",
        help="Fetch a lightweight UniRef cluster view",
        summary="Fetch a reduced UniRef cluster projection.",
    ),
    ShortcutCommand(
        group="uniref",
        name="members",
        operation_key="uniref.members",
        identifier_name="id",
        identifier_metavar="ID",
        help="List members of a UniRef cluster",
        summary="List the members that belong to a UniRef cluster.",
    ),
    ShortcutCommand(
        group="uniref",
        name="members-stream",
        operation_key="uniref.members-stream",
        identifier_name="id",
        identifier_metavar="ID",
        help="Stream members of a UniRef cluster",
        summary="Stream all members of a UniRef cluster in one response.",
    ),
    ShortcutCommand(
        group="uniparc",
        name="light",
        operation_key="uniparc.light",
        identifier_name="upi",
        identifier_metavar="UPI",
        help="Fetch a lightweight UniParc entry",
        summary="Fetch a reduced UniParc entry projection.",
    ),
    ShortcutCommand(
        group="uniparc",
        name="databases",
        operation_key="uniparc.databases",
        identifier_name="upi",
        identifier_metavar="UPI",
        help="List cross-database records for a UniParc entry",
        summary="List cross-database records linked to a UniParc sequence.",
    ),
    ShortcutCommand(
        group="uniparc",
        name="databases-stream",
        operation_key="uniparc.databases-stream",
        identifier_name="upi",
        identifier_metavar="UPI",
        help="Stream cross-database records for a UniParc entry",
        summary="Stream cross-database records linked to a UniParc sequence.",
    ),
    ShortcutCommand(
        group="uniparc",
        name="proteome",
        operation_key="uniparc.proteome",
        identifier_name="upId",
        identifier_metavar="UPID",
        help="List UniParc sequences linked to a proteome",
        summary="List UniParc sequences associated with a proteome identifier.",
    ),
    ShortcutCommand(
        group="uniparc",
        name="proteome-stream",
        operation_key="uniparc.proteome-stream",
        identifier_name="upId",
        identifier_metavar="UPID",
        help="Stream UniParc sequences linked to a proteome",
        summary="Stream UniParc sequences associated with a proteome identifier.",
    ),
    ShortcutCommand(
        group="proteomes",
        name="genecentric-entry",
        operation_key="proteomes.genecentric-entry",
        identifier_name="accession",
        identifier_metavar="ACCESSION",
        help="Fetch a gene-centric proteome view by accession",
        summary="Fetch a gene-centric proteome grouping by accession.",
    ),
    ShortcutCommand(
        group="proteomes",
        name="genecentric-upid-entry",
        operation_key="proteomes.genecentric-upid-entry",
        identifier_name="upid",
        identifier_metavar="UPID",
        help="Fetch a gene-centric proteome view by proteome ID",
        summary="Fetch a gene-centric proteome grouping by proteome identifier.",
    ),
)

SPECIALIZED_SHORTCUTS_BY_PATH = {
    (item.group, item.name): item for item in SPECIALIZED_SHORTCUTS
}

TOP_LEVEL_COMMANDS = (
    {
        "command": "get-entry",
        "summary": "Fetch one record by identifier from supported datasets.",
        "datasets": [
            {"dataset": dataset, "operation_key": operation_key, "identifier": path_param}
            for dataset, (operation_key, path_param) in sorted(ENTRY_DATASETS.items())
        ],
    },
    {
        "command": "search",
        "summary": "Run paginated searches against supported datasets.",
        "datasets": [
            {"dataset": dataset, "operation_key": operation_key}
            for dataset, operation_key in sorted(SEARCH_DATASETS.items())
        ],
    },
    {
        "command": "stream",
        "summary": "Run streamed bulk searches against supported datasets.",
        "datasets": [
            {"dataset": dataset, "operation_key": operation_key}
            for dataset, operation_key in sorted(STREAM_DATASETS.items())
        ],
    },
    {
        "command": "idmapping",
        "summary": "Submit, inspect, and retrieve asynchronous ID mapping jobs.",
        "subcommands": [
            {"name": "run", "operation_key": "idmapping.run"},
            {"name": "status", "operation_key": "idmapping.status"},
            {"name": "details", "operation_key": "idmapping.details"},
        ]
        + [
            {
                "name": f"results --target {target}",
                "operation_key": search_operation,
                "stream_operation_key": stream_operation,
            }
            for target, (search_operation, stream_operation) in sorted(
                IDMAPPING_RESULT_OPERATIONS.items()
            )
        ],
    },
    {
        "command": "request",
        "summary": "Call any bundled OpenAPI operation directly by operation key.",
    },
    {
        "command": "docs",
        "summary": "Show CLI and endpoint documentation for the bundled surface.",
    },
    {
        "command": "cache",
        "summary": "Inspect and manage the on-disk GET response cache.",
        "subcommands": [{"name": name} for name in ("stats", "prune", "clear")],
    },
)
