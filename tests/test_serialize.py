"""The shared result serializer — the contract the CLI and the web API both depend on."""

from __future__ import annotations

from sdb.cli import _result_to_dict
from sdb.engine.pipeline import discover
from sdb.graph.build import KnowledgeGraph
from sdb.serialize import hop_dicts, result_core, source_dicts, unique_sources

# Every field both surfaces agree on. `sources` is intentionally absent: each caller appends it last
# so both payloads keep their original key order (see the sdb.serialize module docstring).
_SHARED_FIELDS = {
    "archetype",
    "topic",
    "endpoint",
    "hops",
    "score",
    "trust",
    "surprise",
    "endpoint_unexpectedness",
    "possibly",
    "til",
}

# Every field of a `chain` step. `evidence` is the curated justification (ADR 0037).
_CHAIN_FIELDS = {"from", "from_id", "phrase", "to", "to_id", "evidence"}


def _a_result(graph: KnowledgeGraph):
    return discover(graph, "Roman Empire", top=1)[0]


def test_result_core_carries_the_shared_fields_and_not_sources(seed_graph: KnowledgeGraph) -> None:
    core = result_core(seed_graph, _a_result(seed_graph), score_dp=4, trust_dp=4, metric_dp=4)
    assert set(core) == _SHARED_FIELDS


def test_both_surfaces_expose_every_shared_field(seed_graph: KnowledgeGraph) -> None:
    """The point of the shared core: a new field can't reach one surface and miss the other.

    Both are asserted against the *same* set, so adding a key to `result_core` without teaching
    `_SHARED_FIELDS` fails here rather than silently shipping a half-populated payload.
    """
    from sdb.web import _result_payload

    result = _a_result(seed_graph)
    cli = _result_to_dict(seed_graph, result, 1)
    web = _result_payload(seed_graph, result)

    assert set(cli) >= _SHARED_FIELDS
    assert set(web) >= _SHARED_FIELDS
    # The shared values agree up to each surface's own rounding (the CLI keeps more precision).
    assert cli["topic"] == web["topic"]
    assert cli["endpoint"] == web["endpoint"]
    assert cli["til"] == web["til"]
    assert cli["hops"] == web["hops"]
    assert round(float(cli["trust"]), 3) == web["trust"]


def test_hop_dicts_render_one_sourced_step_per_hop(seed_graph: KnowledgeGraph) -> None:
    result = _a_result(seed_graph)
    steps = hop_dicts(seed_graph, result)

    assert len(steps) == result.path.length
    assert all(set(step) == _CHAIN_FIELDS for step in steps)
    # Each step joins onto the next, and the whole chain spans the path's endpoints.
    assert [step["from_id"] for step in steps] == list(result.path.node_ids[:-1])
    assert [step["to_id"] for step in steps] == list(result.path.node_ids[1:])


def test_hop_dicts_carry_each_statement_s_own_curated_evidence(seed_graph: KnowledgeGraph) -> None:
    """The evidence must be the hop's *own* claim, not the path's or the neighbour's (ADR 0037)."""
    result = _a_result(seed_graph)
    steps = hop_dicts(seed_graph, result)

    for step, hop in zip(steps, result.path.hops, strict=True):
        assert step["evidence"] == hop.statement.evidence
    assert all(step["evidence"] for step in steps)  # the curated seed justifies every hop


def test_both_surfaces_expose_the_same_evidence_chain(seed_graph: KnowledgeGraph) -> None:
    """`chain` is shared, so evidence cannot ship to one surface and silently miss the other."""
    from sdb.web import _result_payload

    result = _a_result(seed_graph)
    cli = _result_to_dict(seed_graph, result, 1)
    web = _result_payload(seed_graph, result)

    assert cli["chain"] == web["chain"]
    assert all(set(step) == _CHAIN_FIELDS for step in cli["chain"])


def test_sources_stay_last_in_both_payloads(seed_graph: KnowledgeGraph) -> None:
    """Key order is not semantic, but it is a published output shape — keep it stable."""
    from sdb.web import _result_payload

    result = _a_result(seed_graph)
    assert list(_result_to_dict(seed_graph, result, 1))[-1] == "sources"
    assert list(_result_payload(seed_graph, result))[-1] == "sources"


def test_sources_are_deduplicated_by_id_in_first_seen_order(seed_graph: KnowledgeGraph) -> None:
    result = _a_result(seed_graph)
    ids = [source.id for source in unique_sources(result)]
    assert ids == list(dict.fromkeys(ids))  # no duplicates, order preserved

    dicts = source_dicts(result)
    assert [d["id"] for d in dicts] == ids
    assert all({"id", "type", "url"} == set(d) for d in dicts)
