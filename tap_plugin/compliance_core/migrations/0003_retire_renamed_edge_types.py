"""Delete edges of the two edge types renamed for edge-naming conformance (Issue# 5).

`HAS_COMPLIANCE_EVIDENCE` became `CITES_COMPLIANCE_EVIDENCE` and `HAS_COMPLIANCE_FINDING` became
`CARRIES_COMPLIANCE_FINDING` (core's `req-tap-plugin-edge-naming`, rule `modal-prefix`). This
plugin ships no collector, but its edges land on the grid through consumers' collectors, and a
renamed type is a NEW edge on their next run: the old rows would linger as unregistered types
nothing reads. This removes them (with their spine rows) so a grid upgraded in place is not left
carrying two generations of the same relation. Nodes are untouched; the next collection
repopulates the new types.

Modelled on tap-plugin-github-core's `0013_retire_renamed_edge_types`. Direct ORM access is the
sanctioned path in migrations.
"""

from typing import Any

from django.db import migrations

_RETIRED_EDGE_TYPES = (
    "HAS_COMPLIANCE_EVIDENCE__compliance_core",
    "HAS_COMPLIANCE_FINDING__compliance_core",
)


def delete_retired_edges(apps: Any, schema_editor: Any) -> None:
    Edge = apps.get_model("tap_grid", "Edge")
    Entity = apps.get_model("tap_grid", "Entity")
    edges = Edge.objects.filter(edge_type__in=_RETIRED_EDGE_TYPES)
    entity_ids = list(edges.values_list("entity_id", flat=True))
    edges.delete()
    Entity.objects.filter(pk__in=entity_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("compliance_core", "0002_initial"),
        ("tap_grid", "0001_initial"),
    ]

    operations = [migrations.RunPython(delete_retired_edges, migrations.RunPython.noop)]
