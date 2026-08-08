"""Shared machinery the lesson generators draw on.

Every module here is private. It holds the constructions that more than one
lesson needs — scene builders, nonce-word factories, proof search, small
solvers — so that a lesson module contains the lesson and nothing else.

One module per section of the curriculum, mirroring
:mod:`langcurriculum.lessons`, plus :mod:`langcurriculum._support.base` for the
vocabulary and scene helpers that the whole curriculum shares.
"""
