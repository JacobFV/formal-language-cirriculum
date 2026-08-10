"""Curricula are opinions about lessons. These tests hold them to being usable ones."""

from __future__ import annotations

import pytest

import langcurriculum as lc
from langcurriculum.curricula import Curriculum, CurriculumError, Node, curriculum_ids
from langcurriculum.curricula.graph import derive_edges, transitive_reduction


@pytest.mark.parametrize("name", curriculum_ids())
def test_every_shipped_curriculum_is_a_usable_graph(name):
    c = lc.curriculum(name)
    c.validate(known_lessons=lc.REGISTRY)
    assert c.nodes and c.title
    assert len(c.linearize()) == len(c.nodes)


@pytest.mark.parametrize("name", curriculum_ids())
def test_linearizing_is_deterministic(name):
    c = lc.curriculum(name)
    assert c.linearize() == c.linearize()


@pytest.mark.parametrize("name", curriculum_ids())
def test_every_flattening_respects_every_edge(name):
    """The property that makes a flattening a teaching order at all."""
    c = lc.curriculum(name)
    for order in c.linearizations(6):
        place = {n.key: i for i, n in enumerate(order)}
        assert len(place) == len(c.nodes)
        for a, b in c.edges:
            assert place[a] < place[b], f"{name}: {a} after {b}"


def test_a_graph_with_width_has_more_than_one_flattening():
    """'One of many possible flattenings' has to actually be many."""
    c = lc.curriculum("progressive")
    orders = [tuple(n.key for n in o) for o in c.linearizations(6)]
    assert len(set(orders)) > 1


def test_curricula_disagree_about_the_same_lessons():
    """The point of the refactor: two opinions, same material."""
    a = [n.lesson for n in lc.curriculum("core170").linearize()]
    b = [n.lesson for n in lc.curriculum("progressive").linearize()]
    shared = set(a) & set(b)
    assert len(shared) > 100
    assert [x for x in a if x in shared] != [x for x in b if x in shared]


def test_layers_are_consistent_with_edges():
    c = lc.curriculum("progressive")
    depth = c.layers()
    for a, b in c.edges:
        assert depth[a] < depth[b]


def test_ancestors_and_descendants_are_transitive_and_disjoint():
    c = lc.curriculum("progressive")
    key = max(c.keys, key=lambda k: len(c.ancestors(k)))
    anc, desc = c.ancestors(key), c.descendants(key)
    assert anc and not (anc & desc), "a DAG cannot have a node both above and below"
    for a in anc:
        assert c.ancestors(a) <= anc


def test_frontier_walks_the_whole_graph_and_never_jumps_an_edge():
    c = lc.curriculum("progressive")
    mastered: set[str] = set()
    steps = 0
    while len(mastered) < len(c.nodes):
        available = c.frontier(mastered)
        assert available, "the frontier went empty before the graph was covered"
        for node in available:
            assert all(p in mastered for p in c.prerequisites(node.key))
        mastered.add(available[0].key)
        steps += 1
        assert steps <= len(c.nodes) + 1
    assert mastered == set(c.keys)


def test_compositional_splits_are_disjoint_by_construction():
    """The measurement the graph exists to produce."""
    rows = lc.dataset.compositional_splits("progressive")
    assert rows, "an edgeless graph affords no splits; progressive must have some"
    for r in rows:
        assert r["train"] and r["eval"]
        assert not set(r["train"]) & set(r["eval"])


def test_derived_edges_are_justified_by_the_axes():
    c = lc.curriculum("progressive")
    for a, b in c.edges:
        la, lb = lc.get(a), lc.get(b)
        keys = set(la.axes) | set(lb.axes)
        assert all(la.axes.get(k, 0) <= lb.axes.get(k, 0) for k in keys), (a, b)
        assert any(la.axes.get(k, 0) < lb.axes.get(k, 0) for k in keys), (a, b)
        assert set(la.tags) & set(lb.tags) or set(la.capabilities) & set(lb.capabilities)


def test_transitive_reduction_removes_only_implied_edges():
    nodes = ["a", "b", "c"]
    assert transitive_reduction(nodes, [("a", "b"), ("b", "c"), ("a", "c")]) == \
        (("a", "b"), ("b", "c"))


def test_a_cycle_is_rejected_rather_than_walked():
    c = Curriculum(id="bad", title="bad", nodes=(Node("a"), Node("b")),
                   edges=(("a", "b"), ("b", "a")))
    with pytest.raises(CurriculumError, match="cycle"):
        c.validate()


def test_an_unknown_lesson_is_rejected_at_validation():
    c = Curriculum(id="bad", title="bad", nodes=(Node("no_such_lesson"),))
    with pytest.raises(CurriculumError, match="unknown lessons"):
        c.validate(known_lessons=lc.REGISTRY)


def test_a_duplicate_node_key_is_rejected_at_construction():
    with pytest.raises(CurriculumError, match="duplicate"):
        Curriculum(id="bad", title="bad", nodes=(Node("a"), Node("a")))


def test_the_same_lesson_can_appear_twice_through_different_surfaces():
    """A cross-modal transfer claim, which is an edge you can actually test."""
    base = Curriculum(id="b", title="b", nodes=(Node("unification"),))
    rast = base.with_presentation("english/inline_bare/raster", id="b_raster")
    joined = base.merge(rast, id="cross").validate(known_lessons=lc.REGISTRY)
    joined = Curriculum(id="cross", title="cross", nodes=joined.nodes,
                        edges=(("unification", "unification@english/inline_bare/raster"),))
    joined.validate(known_lessons=lc.REGISTRY)
    assert joined.lessons == ("unification",)
    assert len(joined.nodes) == 2
    train, ev = joined.train_eval_split("unification@english/inline_bare/raster")
    assert train == ("unification",) and ev == ("unification",)


def test_tag_and_capability_curricula_are_built_on_demand():
    c = lc.curriculum("tag:mathematics")
    assert c.nodes and all("mathematics" in lc.get(n.lesson).tags for n in c)
    with pytest.raises(CurriculumError):
        lc.curriculum("tag:no_such_tag")


def test_an_unknown_curriculum_names_the_ones_that_exist():
    with pytest.raises(CurriculumError, match="core170"):
        lc.curriculum("nonsense")
