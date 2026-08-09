"""Shared fixtures, and the one thing every test file needs to agree about.

The package ships five hand-written grammars that work from a clone, and four
hundred derived ones that need a language database built from public datasets.
That database is eight gigabytes and is not committed, so **the suite must pass
without it** — a fresh clone that cannot run its own tests is a fresh clone
nobody can contribute to.

:data:`needs_db` is how a test says it is about the derived half. It lived in
one test module and the other did not import it, so a test asserting Turkish's
imported vocabulary failed rather than skipped on a machine with no database.
Keeping the marker here means there is one definition to get right.
"""

from __future__ import annotations

import pytest

from langcurriculum.grammar.store import LanguageDB

#: the process-wide handle; opening it is cheap and reading it is lazy
DB = LanguageDB()

#: Skip a test that cannot run without the language database. The message says
#: how to build it, because a skip whose cause is unclear is a test nobody fixes.
needs_db = pytest.mark.skipif(
    not DB.exists(),
    reason="language database absent; build it with "
           "`python scripts/build_langdb.py --raw <dir> --fetch`")


@pytest.fixture(scope="session")
def language_db() -> LanguageDB:
    return DB
