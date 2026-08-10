"""The cache is a cache. These tests hold it to never being anything more."""

from __future__ import annotations

import hashlib

import pytest

import langcurriculum as lc
from langcurriculum.address import Address, Space, batch
from langcurriculum.presentation import Presentation
from langcurriculum.store import (CACHEABLE, CachedRenderer, LocalStore, S3Store,
                                  store_from_env)

RASTER = Presentation(surface="raster")


@pytest.fixture()
def store(tmp_path):
    return LocalStore(tmp_path / "cache")


def test_a_local_store_round_trips(store):
    store.put("k", b"bytes")
    assert store.get("k") == b"bytes"
    assert store.has("k")
    assert store.get("missing") is None and not store.has("missing")


def test_writes_are_atomic_enough_to_never_be_read_half_written(store, tmp_path):
    store.put("k", b"x" * 10_000)
    leftovers = list((tmp_path / "cache").rglob("*.tmp"))
    assert not leftovers, "a temporary file was left where a reader could find it"


def test_the_second_render_of_an_address_comes_from_the_cache(store):
    r = CachedRenderer(store)
    a = Address("unification", 3, presentation=RASTER)
    first, second = r.content(a), r.content(a)
    assert (r.misses, r.hits) == (1, 1)
    assert first.assets[0].sha256 == second.assets[0].sha256
    assert second.meta.get("cached") is True


def test_text_is_never_cached_because_regenerating_it_is_cheaper(store):
    r = CachedRenderer(store)
    r.content(Address("unification", 3))
    assert (r.skipped, r.hits, r.misses) == (1, 0, 0)
    assert "text" not in CACHEABLE


def test_a_missing_store_is_not_an_error():
    """A cache is an optimization; losing it must never stop a render."""
    r = CachedRenderer(None)
    content = r.content(Address("unification", 3, presentation=RASTER))
    assert content.assets and r.skipped == 1


def test_the_renderer_version_is_in_the_cache_key_but_not_the_episode_key():
    """The failure this prevents has already happened once, to the site."""
    a = Address("unification", 1, presentation=RASTER)
    assert "raster_v" in a.cache_key()
    assert "raster_v" not in a.key()
    stale = a.digest()
    assert a.digest(renderer_version="raster_v99") != stale


def test_two_surfaces_of_one_episode_do_not_share_a_slot(store):
    r = CachedRenderer(store)
    r.content(Address("unification", 4, presentation=RASTER))
    r.content(Address("unification", 4, presentation=Presentation(surface="audio")))
    assert r.misses == 2 and r.hits == 0


def test_warming_a_batch_reports_what_it_did(store):
    space = Space(lessons=("unification",), seeds=(0, 20), presentations=(RASTER,))
    tallies = CachedRenderer(store).warm(batch(space, 0, 4))
    assert tallies["misses"] == 4 and tallies["hits"] == 0
    assert CachedRenderer(store).warm(batch(space, 0, 4))["hits"] == 4


# ---------------------------------------------------------------- S3 / R2
def test_no_credentials_means_no_cache_rather_than_an_error():
    assert store_from_env({}) is None
    assert store_from_env({"R2_BUCKET": "b"}) is None


def test_a_local_cache_directory_wins_when_named(tmp_path):
    s = store_from_env({"LANGCURRICULUM_CACHE": str(tmp_path)})
    assert isinstance(s, LocalStore)


def test_r2_is_built_from_the_usual_variables():
    s = store_from_env({"R2_ACCOUNT_ID": "acct", "R2_BUCKET": "bkt",
                        "R2_ACCESS_KEY_ID": "key", "R2_SECRET_ACCESS_KEY": "secret"})
    assert isinstance(s, S3Store)
    assert s.endpoint == "https://acct.r2.cloudflarestorage.com"
    assert s.region == "auto"


def test_the_signature_is_a_well_formed_sigv4_header():
    """Signed by hand, so it is worth checking the shape rather than trusting it."""
    s = S3Store(bucket="b", endpoint="https://e.example", access_key="AK",
                secret_key="SK")
    empty = hashlib.sha256(b"").hexdigest()
    h = s._headers("GET", "obj", empty)
    auth = h["authorization"]
    assert auth.startswith("AWS4-HMAC-SHA256 Credential=AK/")
    assert "/auto/s3/aws4_request" in auth
    assert "SignedHeaders=host;x-amz-content-sha256;x-amz-date" in auth
    assert len(auth.rsplit("Signature=", 1)[1]) == 64
    assert h["x-amz-content-sha256"] == empty


def test_signing_covers_the_body_it_is_sending():
    s = S3Store(bucket="b", endpoint="https://e.example", access_key="AK",
                secret_key="SK")
    a = s._headers("PUT", "obj", hashlib.sha256(b"one").hexdigest())
    b = s._headers("PUT", "obj", hashlib.sha256(b"two").hexdigest())
    assert a["authorization"] != b["authorization"]
