"""Addressing, and drawing batches from a space nobody can enumerate."""

from __future__ import annotations

import pytest

import langcurriculum as lc
from langcurriculum.address import Address, Space, batch, draw, permute
from langcurriculum.dataset import held_out, invariance_set
from langcurriculum.presentation import Presentation

SPACE = Space(lessons=("unification", "negation", "symbol_grounding"),
              seeds=(0, 500),
              difficulties=(None, 0.5),
              presentations=(Presentation(), Presentation(answer_format="labelled_label"),
                             Presentation(surface="raster")))


def test_an_address_reproduces_its_episode():
    a = Address("symbol_grounding", 12, presentation=Presentation())
    assert a.example().prompt == lc.get("symbol_grounding").example(12).prompt


def test_the_cache_key_names_the_renderer_and_the_plain_key_does_not():
    a = Address("unification", 1, presentation=Presentation(surface="raster"))
    assert "raster_v1" in a.cache_key()
    assert "raster_v1" not in a.key()
    assert a.digest() != Address("unification", 2,
                                 presentation=Presentation(surface="raster")).digest()


def test_two_surfaces_of_one_episode_share_an_instance_but_not_a_cache_key():
    text = Address("unification", 5)
    rast = Address("unification", 5, presentation=Presentation(surface="raster"))
    assert text.instance() == rast.instance()
    assert text.cache_key() != rast.cache_key()


# ---------------------------------------------------------------- permutation
@pytest.mark.parametrize("size", [1, 2, 3, 7, 64, 1000, 4096, 100_003])
def test_the_permutation_is_a_bijection(size):
    probe = range(size) if size <= 4096 else range(0, size, 997)
    seen = {permute(i, size) for i in probe}
    assert len(seen) == len(list(probe))
    assert all(0 <= v < size for v in seen)


def test_the_permutation_is_stable_across_calls():
    assert [permute(i, 5000) for i in range(20)] == [permute(i, 5000) for i in range(20)]


def test_the_permutation_actually_shuffles():
    assert [permute(i, 10_000) for i in range(20)] != list(range(20))


def test_an_index_outside_the_space_is_refused():
    with pytest.raises(IndexError):
        permute(10, 10)


# ---------------------------------------------------------------- spaces
def test_a_space_is_far_larger_than_anything_drawn_from_it():
    assert len(SPACE) == 3 * 500 * 2 * 3 == 9000
    assert SPACE.describe()["size"] == 9000


def test_raw_indexing_covers_every_axis_exactly_once():
    seen = {SPACE.at(i).key() for i in range(len(SPACE))}
    assert len(seen) == len(SPACE)


def test_batches_that_do_not_share_indices_do_not_share_episodes():
    """Disjointness by construction, which is the only kind worth having."""
    a = {ad.key() for ad in batch(SPACE, 0, 300)}
    b = {ad.key() for ad in batch(SPACE, 300, 300)}
    assert len(a) == len(b) == 300
    assert not (a & b)


def test_a_batch_is_reproducible_from_its_index_alone():
    assert [a.key() for a in batch(SPACE, 77, 10)] == [a.key() for a in batch(SPACE, 77, 10)]


def test_drawing_reaches_every_axis_value():
    drawn = [draw(SPACE, i) for i in range(2000)]
    assert {a.lesson for a in drawn} == set(SPACE.lessons)
    assert {a.presentation.key() for a in drawn} == {p.key() for p in SPACE.presentations}
    assert {a.difficulty for a in drawn} == set(SPACE.difficulties)


def test_an_empty_space_is_refused():
    with pytest.raises(ValueError):
        Space(lessons=())
    with pytest.raises(ValueError):
        Space(lessons=("unification",), seeds=(5, 5))


# ---------------------------------------------------------------- splits
def test_held_out_partitions_without_overlap_and_is_stable():
    langs = ["english", "spanish", "chinese", "turkish", "swahili", "fin", "pol", "jpn"]
    s = held_out(langs)
    assert set(s["train"]) | set(s["eval"]) == set(langs)
    assert not set(s["train"]) & set(s["eval"])
    assert held_out(langs) == s


def test_held_out_does_not_reshuffle_when_a_value_is_added():
    """A hash, not a slice — so yesterday's split survives tomorrow's new language."""
    a = held_out(["a", "b", "c", "d"])
    b = held_out(["a", "b", "c", "d", "e"])
    for v in "abcd":
        assert (v in a["eval"]) == (v in b["eval"])


def test_seed_splits_cannot_overlap():
    s = lc.splits(train=1000, eval=200)
    (t0, tn), (e0, en) = s["train"], s["eval"]
    assert t0 + tn <= e0


# ---------------------------------------------------------------- invariance
def test_an_invariance_set_is_one_problem_through_several_surfaces():
    rows = invariance_set("unification", 4,
                          ["english", "english/labelled_label", "spanish"])
    assert len({r["instance_id"] for r in rows}) == 1
    assert len({r["presentation"] for r in rows}) == 3
    assert len({r["answer"] for r in rows}) <= 2      # translation may rename it
