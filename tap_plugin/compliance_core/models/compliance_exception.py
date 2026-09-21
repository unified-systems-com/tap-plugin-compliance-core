"""Exception — a formal acceptance of one or more findings."""

from typing import Any, ClassVar

from django.db import models

from tap_grid.models import BaseModel


class ComplianceException(BaseModel):
    """An exception covers one or more findings, formally accepting the risk they represent.

    The Python class is `ComplianceException` rather than `Exception` to avoid
    shadowing the Python built-in in any module that imports this model. The
    entity-type slug is `compliance_core__compliance_exception` — that's what
    GRIFT, the service layer, and the rest of TAP see externally.

    Regime-agnostic substrate: an exception formally accepts a finding under any
    regime; the regime is layered per-instance, not baked into the model.

    v1 shape is minimal: name, description, status. By convention the `description`
    carries the business justification. Additional workflow fields (expiration_date,
    approver, review cadence) are deferred as explicit Future work in the spec.

    Identity (`req-compliance-core-identity`): found again by the system of record that
    granted it and that system's own reference — `("source", "source_key")`. A producer that
    writes neither gets a fresh node every run rather than an error, so writing them is the
    data contract a minting plugin owes this one.

    Spec: plugins/compliance_core/specs/spec-compliance-core-v0.md
    """

    ENTITY_TYPE: ClassVar[str] = "compliance_core__compliance_exception"
    # WHO granted it, and WHAT THEY CALL IT. An exception is a decision recorded in some system
    # of record — a GRC tool, a risk register, a ticket — and that system's own reference is the
    # only stable handle on it; `name` is a label a reviewer rewrites and `status` is the thing
    # that CHANGES (active → expired → revoked), which is exactly what a key must not be
    # (Issue# 8 - tap-plugin-compliance-core). An exception authored by hand inside TAP carries
    # neither field, is created once by an explicit write, and is never re-observed — so nothing
    # is lost there; what would be lost under KEYLESS is the re-import of an exception register.
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("source", "source_key")
    ENTITY_NAME: ClassVar[str] = "Exception"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A formal acceptance of one or more findings, typically recording "
        "the rationale for not remediating."
    )
    ENTITY_ICON: ClassVar[str] = "exception"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {"compliance": "exception"}

    _STATUS_VALUES = ["active", "expired", "revoked"]

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "source": {"type": "string", "maxLength": 64},
        "source_key": {"type": "string", "maxLength": 512},
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "status": {"type": "string", "enum": _STATUS_VALUES},
    }

    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        "source": {"validation": "jsonschema", "schema": {"type": "string", "maxLength": 64}},
        "source_key": {"validation": "jsonschema", "schema": {"type": "string", "maxLength": 512}},
        "name": {
            "validation": "jsonschema",
            "schema": {"type": "string", "minLength": 1},
        },
        "description": {"validation": "jsonschema", "schema": {"type": "string"}},
        "status": {
            "validation": "jsonschema",
            "schema": {"type": "string", "enum": _STATUS_VALUES},
        },
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["name"]

    #: The producer that asserted this exception — the slug of the plugin that minted it,
    #: never a display name. Half of the natural key: it namespaces `source_key`, so
    #: two producers can never collide.
    source = models.CharField(max_length=64, blank=True, default="")
    #: What the producing system calls this exception, verbatim ("GRC-1184").
    #: Opaque here: only the producer's namespace gives it meaning, and compliance_core
    #: never parses it.
    source_key = models.CharField(max_length=512, blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, blank=True, default="active", db_index=True)

    class Meta(BaseModel.Meta):
        db_table = "compliance_core__compliance_exception"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
