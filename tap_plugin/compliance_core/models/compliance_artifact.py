"""ComplianceArtifact — a fetched compliance document kept whole."""

from typing import Any, ClassVar

from django.db import models

from tap_grid.models import BaseModel


class ComplianceArtifact(BaseModel):
    """A fetched compliance rendering kept whole — OSCAL SSP, OSCAL POA&M, IIW.

    These are downstream renderings of the same canonical inventory the KSI
    signal carries (`build-iiw.py` / `build-oscal-ssp.py` read the signal as
    their source). Decomposing them would re-model that inventory, so they are
    kept whole: typed metadata + the document as a blob. One model; `kind`
    discriminates.

    Regime-agnostic: any compliance regime fetches evidence documents. The
    minting collector stamps the regime dimension per-instance; the model
    default carries only a neutral type marker.

    Identity (`req-compliance-core-identity`): found again by the fetcher that retrieved it
    and that fetcher's own key — `("source", "source_key")`, NOT `source_url`; see the
    declaration below for why the fetch address is not the document's identity.

    Spec: plugins/compliance_core/specs/spec-compliance-core-v0.md
    (req-compliance-core-models).
    """

    ENTITY_TYPE: ClassVar[str] = "compliance_core__compliance_artifact"
    # WHO fetched it, and WHAT THEY CALL IT. `source_url` was considered as the key and refused:
    # it records WHERE a fetch went, which is not the same fact as WHICH DOCUMENT this is. A
    # `…/latest/ssp.json` URL serves a different document every quarter, and a document built
    # locally has no URL at all — so keying on the URL would either collapse successive
    # documents into one row or leave a whole class of artifacts unfindable. The fetcher is the
    # only party that knows which of its documents this is, so it says so: `source_key` is
    # whatever it calls this artifact (often, but not necessarily, the URL it used), and
    # `source_url` keeps the fetch address as the observation it is (Issue# 8 -
    # tap-plugin-compliance-core).
    NATURAL_KEY: ClassVar[tuple[str, ...]] = ("source", "source_key")
    ENTITY_NAME: ClassVar[str] = "Compliance Artifact"
    ENTITY_DESCRIPTION: ClassVar[str] = (
        "A fetched compliance rendering kept whole — an OSCAL SSP, OSCAL "
        "POA&M, or IIW inventory — with fetch and signature-verification "
        "metadata and the document body retained."
    )
    ENTITY_ICON: ClassVar[str] = "compliance-artifact"
    DEFAULT_DIMENSIONS: ClassVar[dict[str, str]] = {"compliance": "compliance-artifact"}

    # Signed file artifact — render as a file card in graph views: pale-olive
    # rectangle (light fill, saturated border) matching the AWS leaf-node pattern
    # so the document glyph stays a clean glyph and the title isn't lost against a
    # dark fill. Name sits bottom-center, outside the box, on the canvas.
    DEFAULT_DISPLAY: ClassVar[dict[str, Any]] = {
        "tap_viz": {
            "shape": "rectangle",
            "colors": {"fill": "#EAE4C0", "border": "#8C7A1E", "label": "#463B08"},
            "label": {"valign": "bottom", "halign": "center", "position": "outside"},
        }
    }

    _KIND_VALUES = ["oscal_ssp", "oscal_poam", "iiw", ""]

    FIELD_CRUD_SCHEMA: ClassVar[dict[str, Any]] = {
        "source": {"type": "string", "maxLength": 64},
        "source_key": {"type": "string", "maxLength": 512},
        "name": {"type": "string", "minLength": 1},
        "kind": {"type": "string"},
        "source_url": {"type": "string"},
        "content_type": {"type": "string"},
        "fetched_at": {"type": "string"},
        "size_bytes": {"type": ["integer", "null"]},
        "content": {"type": ["object", "string", "array", "null"]},
        "signature_verified": {"type": ["boolean", "null"]},
        "signed_by": {"type": "string"},
        "rekor_log_index": {"type": "string"},
        "verified_at": {"type": "string"},
    }

    FIELD_VALIDATION_SCHEMA: ClassVar[dict[str, Any]] = {
        "source": {"validation": "jsonschema", "schema": {"type": "string", "maxLength": 64}},
        "source_key": {"validation": "jsonschema", "schema": {"type": "string", "maxLength": 512}},
        "name": {"validation": "jsonschema", "schema": {"type": "string", "minLength": 1}},
        "kind": {"validation": "jsonschema", "schema": {"type": "string", "enum": _KIND_VALUES}},
        "size_bytes": {"validation": "jsonschema", "schema": {"type": ["integer", "null"]}},
        "signature_verified": {"validation": "jsonschema", "schema": {"type": ["boolean", "null"]}},
    }
    CREATE_REQUIRED: ClassVar[list[str]] = ["name", "kind"]

    #: The producer that asserted this artifact — the slug of the plugin that minted it,
    #: never a display name. Half of the natural key: it namespaces `source_key`, so
    #: two producers can never collide.
    source = models.CharField(max_length=64, blank=True, default="")
    #: What the producing system calls this artifact, verbatim ("https://acme.example/ssp.json@v3").
    #: Opaque here: only the producer's namespace gives it meaning, and compliance_core
    #: never parses it.
    source_key = models.CharField(max_length=512, blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")
    kind = models.CharField(max_length=32, blank=True, default="", db_index=True)
    source_url = models.CharField(max_length=512, blank=True, default="")
    content_type = models.CharField(max_length=128, blank=True, default="")
    fetched_at = models.CharField(max_length=64, blank=True, default="")
    size_bytes = models.BigIntegerField(blank=True, null=True)
    # The document body — a parsed dict for OSCAL JSON, raw text for IIW CSV.
    content = models.JSONField(default=dict, blank=True)
    # Signature verification result — populated by the collector.
    signature_verified = models.BooleanField(blank=True, null=True)
    signed_by = models.CharField(max_length=512, blank=True, default="")
    rekor_log_index = models.CharField(max_length=64, blank=True, default="")
    verified_at = models.CharField(max_length=64, blank=True, default="")

    class Meta(BaseModel.Meta):
        db_table = "compliance_core__compliance_artifact"

    def get_name(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.get_name()
