"""compliance_core declares how each of its rows is found again (Issue# 8 - this repo).

The mechanism under test is core's assigned identity (`req-grid-entity-natural-key`,
`req-compliance-core-identity`): a producer names a node by a batch-local `ref`, and the
GRIFT importer resolves that ref against **the owning model's** `NATURAL_KEY` — this
plugin's declaration, no matter which plugin wrote the node. So these tests stand in for
every producer, `github_core` first among them.

They assert positively rather than asserting the absence of breakage:

- **the declaration exists** for every registered type, because an undeclared type is
  refused outright (*undeclared is never keyless*) and a model added later without one
  would fail a producer's whole batch at run time;
- **re-observation is one node** — two writes of the same source object under one
  producer resolve to the SAME entity id, which is exactly the property `KEYLESS` would
  have lost (a keyless ref mints a new node every run, so a re-scan would duplicate
  every finding rather than re-observe it);
- **the producer's namespace separates producers** — the same `source_key` under two
  slugs is two objects, which is what lets each producer keep its own keying rules;
- **a producer that writes nothing gets nothing** — absent constituting values are a
  hole, and a hole is "not found", so the node is minted fresh. Duplicates, not an
  error. This is the failure mode the neutral columns are designed against, pinned here
  so it is a known cost rather than a surprise.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from tap_plugin.compliance_core.models import ComplianceFinding

from tap_grid.grift import grift_import
from tap_grid.models import Entity
from tap_grid.natural_key import Keyless
from tap_grid.registry import get_model_class, list_entity_types

#: Every type this plugin owns, with the source object one producer would observe twice.
#: One row per model, so a declaration that cannot find its own row is caught by name.
SOURCE_OBJECTS: list[tuple[str, dict[str, Any]]] = [
    (
        "compliance_core__compliance_finding",
        {"name": "CodeQL py/sql-injection", "source": "github_core", "source_key": "acme/app#code_scanning#7"},
    ),
    (
        "compliance_core__compliance_evidence",
        {"name": "SARIF upload", "kind": "scanner_output", "source": "github_core", "source_key": "acme/app#7#sarif"},
    ),
    (
        "compliance_core__compliance_exception",
        {"name": "Accepted for Q4", "source": "github_core", "source_key": "GRC-1184"},
    ),
    (
        "compliance_core__compliance_boundary",
        {"name": "Acme SaaS ATO", "source": "github_core", "source_key": "fedramp/acme-saas-ato"},
    ),
    (
        "compliance_core__compliance_artifact",
        {"name": "Acme SSP", "kind": "oscal_ssp", "source": "github_core", "source_key": "acme/ssp@v3"},
    ),
    (
        "compliance_core__compliance_context",
        {"name": "FedRAMP 20x posture", "regime": "fedramp_20x", "fedramp_class": "b"},
    ),
]


def _doc(entity_type: str, fields: dict[str, Any], ref: str = "it") -> dict[str, Any]:
    """A one-batch GRIFT document naming one node by `ref` — what a producer sends.

    Built here rather than imported from core's own test helpers: this suite also runs
    against a RELEASED core wheel, which ships no test package.
    """
    return {
        "metadata": {"grift_version": "0"},
        "_reserved": {},
        "batches": [
            {
                "batch_entity": {
                    "entity_id": str(uuid.uuid4()),
                    "entity_type": "batch",
                    "name": "identity test batch",
                    "dimensions": {},
                },
                "batch_node": {
                    "name": "identity test batch",
                    "description": "",
                    "description_json": None,
                    "source": "test",
                    "metadata": {},
                },
                "nodes": [
                    {
                        "entity": {
                            "ref": ref,
                            "entity_type": entity_type,
                            "name": fields["name"],
                            "dimensions": {},
                        },
                        "node": dict(fields),
                    }
                ],
                "edges": [],
            }
        ],
    }


def _resolved(entity_type: str, fields: dict[str, Any]) -> str:
    """Import one ref node and return the id core resolved it to."""
    result = grift_import(_doc(entity_type, fields))
    assert result.success, result.errors
    return str(result.imported_batches[0].resolved_refs["it"])


@pytest.mark.django_db
class TestDeclarations:
    def test_every_compliance_core_model_has_declared(self) -> None:
        """Undeclared is never keyless: a ref to an undeclared type is refused outright.

        `resolve_identity` raises rather than guessing, so a model added here without a
        declaration fails a PRODUCER's whole batch at run time, in another repository.
        This is that check at author time, in the repository that owns the declaration.
        """
        undeclared = [
            t
            for t in list_entity_types()
            if t.startswith("compliance_core__") and getattr(get_model_class(t), "NATURAL_KEY", None) is None
        ]
        assert undeclared == [], f"these types would be refused a ref: {undeclared}"

    def test_no_compliance_core_type_is_keyless(self) -> None:
        """KEYLESS is not a safe default here, so nothing may drift into it.

        Every type this plugin owns is re-observed — a scanner re-runs, an artifact is
        re-fetched, a register is re-imported, a posture is re-asserted — and a keyless
        ref mints a NEW node every run. A future type that genuinely observes nothing may
        declare KEYLESS with a reason, and this test is where that decision gets argued.
        """
        keyless = [
            t
            for t in list_entity_types()
            if t.startswith("compliance_core__") and isinstance(get_model_class(t).NATURAL_KEY, Keyless)
        ]
        assert keyless == [], f"these types would mint a new node every run: {keyless}"

    def test_the_declared_fields_exist_on_the_model(self) -> None:
        """A declaration naming a field the table does not have is a citation that does not resolve."""
        for entity_type, _ in SOURCE_OBJECTS:
            model = get_model_class(entity_type)
            names = {f.name for f in model._meta.get_fields()}
            missing = [f for f in model.NATURAL_KEY if f not in names]
            assert missing == [], f"{entity_type} declares fields it does not carry: {missing}"


@pytest.mark.django_db
class TestReObservation:
    def test_two_writes_of_one_source_object_resolve_to_one_node(self) -> None:
        """The done-test of Issue# 8: re-observation is ONE node, per type.

        The second import carries a changed `name` so the assertion cannot pass by the two
        documents being identical: the id is the same because the declared search FOUND the
        first run's row, and the row it found was updated rather than duplicated.
        """
        for entity_type, fields in SOURCE_OBJECTS:
            first = _resolved(entity_type, fields)
            second = _resolved(entity_type, {**fields, "name": fields["name"] + ", re-observed"})
            assert second == first, f"{entity_type} minted a second node for one source object"
            assert uuid.UUID(first).version == 7, "the id is core's to assign, not derived"
            model = get_model_class(entity_type)
            assert model.objects.live().count() == 1, f"{entity_type}: one source object, one row"
            assert Entity.objects.get(pk=uuid.UUID(first)).name.endswith("re-observed")

    def test_one_key_under_two_producers_is_two_nodes(self) -> None:
        """`source` namespaces `source_key`, which is what lets producers keep their own rules.

        Two systems can each call something `7` without either having to know the other
        exists; collapsing them would merge unrelated findings into one node.
        """
        key = {"name": "alert 7", "source_key": "acme/app#7"}
        github = _resolved("compliance_core__compliance_finding", {**key, "source": "github_core"})
        other = _resolved("compliance_core__compliance_finding", {**key, "source": "gitlab_core"})
        assert github != other
        assert ComplianceFinding.objects.live().count() == 2

    def test_a_producer_that_writes_no_key_gets_a_fresh_node_every_time(self) -> None:
        """The designed-against failure mode, pinned so it is a known cost, not a surprise.

        Absent constituting values are a HOLE: the generated search answers "not found"
        without querying rather than matching on nothing, so the node is minted. The result
        is DUPLICATES, not a hard error — which is why the constituting fields are neutral
        ones every producer can write, and why writing them is stated as the data contract
        a minting plugin owes this one.
        """
        bare = {"name": "a finding nobody claimed"}
        first = _resolved("compliance_core__compliance_finding", bare)
        second = _resolved("compliance_core__compliance_finding", bare)
        assert first != second
        assert ComplianceFinding.objects.live().count() == 2

    def test_a_context_is_found_again_by_its_regime(self) -> None:
        """The one type keyed on a field it already carried: one context per regime per Grid.

        A second regime is a second context — the cardinality the model has always claimed,
        now enforced by the search rather than by seeding convention.
        """
        fedramp = _resolved(
            "compliance_core__compliance_context",
            {"name": "FedRAMP posture", "regime": "fedramp_20x", "fedramp_class": "b"},
        )
        again = _resolved(
            "compliance_core__compliance_context",
            {"name": "FedRAMP posture", "regime": "fedramp_20x", "fedramp_class": "c"},
        )
        soc2 = _resolved(
            "compliance_core__compliance_context",
            {"name": "SOC2 posture", "regime": "soc2", "fedramp_class": ""},
        )
        assert again == fedramp and soc2 != fedramp
        model = get_model_class("compliance_core__compliance_context")
        assert model.objects.live().get(entity_id=uuid.UUID(fedramp)).fedramp_class == "c"
