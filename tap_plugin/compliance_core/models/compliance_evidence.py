"""Evidence — an artifact that demonstrates the state of a compliance check."""

from typing import Any, ClassVar

from django.db import models

from tap_grid.models import BaseModel


class ComplianceEvidence(BaseModel):
    """Evidence is a supporting artifact attached to a finding via a CITES_COMPLIANCE_EVIDENCE edge.

    The model is intentionally minimal in v1: name, description, kind. The verdict
    the evidence supports — passing, violation, informational — lives on the
    CITES_COMPLIANCE_EVIDENCE edge as `support_kind`, not on the evidence record
    itself. That keeps a single evidence artifact reusable across multiple findings
    with different relationships.

    Regime-agnostic substrate: evidence supports a finding under any regime; the
    regime is layered per-instance, not baked into the model.

    Identity (`req-compliance-core-identity`): found again by the producer that asserted it
    and that producer's own key — `("source", "source_key")`. A producer that writes neither
    gets a fresh node every run rather than an error, so writing them is the data contract a
    minting plugin owes this one.

    Spec: plugins/compliance_core/specs/spec-compliance-core-v0.md
    """

    ENTITY_TYPE: ClassVar[str] = "compliance_core__compliance_evidence"
    # WHO produced it, and WHAT THEY CALL IT. `name`, `description` and `kind` describe the
    # material, not which piece of material it is: two scanner outputs from consecutive runs
    # share all three. The producing system is the only thing that can say "this is the same
    # artefact I showed you last time", so it says it in a column (Issue# 8 -
    # tap-plugin-compliance-core). KEYLESS was refused: evidence IS re-observed — every rescan
    # re-attaches the same material — and a keyless ref mints a new node every run.
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("source", "source_key")
    ENTITY_NAME: ClassVar[str] = "Evidence"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A supporting artifact for a compliance finding — screenshot, scanner output, "
        "policy document, attestation, log excerpt, or other material."
    )
    ENTITY_ICON: ClassVar[str] = "evidence"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {"compliance": "evidence"}

    _KIND_VALUES = [
        "screenshot",
        "scanner_output",
        "policy_doc",
        "attestation",
        "log_excerpt",
        "other",
    ]

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "source": {"type": "string", "maxLength": 64},
        "source_key": {"type": "string", "maxLength": 512},
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "kind": {"type": "string", "enum": _KIND_VALUES},
    }

    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        "source": {"validation": "jsonschema", "schema": {"type": "string", "maxLength": 64}},
        "source_key": {"validation": "jsonschema", "schema": {"type": "string", "maxLength": 512}},
        "name": {
            "validation": "jsonschema",
            "schema": {"type": "string", "minLength": 1},
        },
        "description": {"validation": "jsonschema", "schema": {"type": "string"}},
        "kind": {
            "validation": "jsonschema",
            "schema": {"type": "string", "enum": _KIND_VALUES},
        },
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["name", "kind"]

    #: The producer that asserted this evidence — the plugin slug of whoever minted it
    #: ("github_core"). Half of the natural key: it namespaces `source_key`.
    source = models.CharField(max_length=64, blank=True, default="")
    #: What the producing system calls this evidence, verbatim ("acme/app#code_scanning#7#sarif").
    #: Opaque here: only the producer's namespace gives it meaning, and compliance_core
    #: never parses it.
    source_key = models.CharField(max_length=512, blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    kind = models.CharField(max_length=32, blank=True, default="other", db_index=True)

    class Meta(BaseModel.Meta):
        db_table = "compliance_core__compliance_evidence"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
