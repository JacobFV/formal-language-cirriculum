# What this is for

This file states the intentions the rest of the repository is built to serve, so
that later work can be conditioned on them rather than guessing from the code.
Where a design decision here conflicts with something convenient, this file wins.

## The purpose

The curriculum exists to **autonomously develop and evaluate symbolic AI**.

It is not a benchmark and not a corpus. It is a generator: an unbounded supply of
synthetic problems, arranged in a curriculum of progressive compositional
complexity, whose ground truth is *computed* rather than annotated. A lesson
invents a grammar, an ontology, a causal graph or a proof calculus, and then
reads the answer off its own construction. There is no labeller to disagree with,
and no held-out sample of anything a model might already have seen.

The question the whole design is bent toward answering is:

> Has the system internalized the **structure** of the problem, or only the
> **surface** it happened to be presented in?

Everything below follows from that question.

## The six decisions

**1. Lessons are flat; curricula are graphs over them.**
A lesson does not know its own position. Ordering, grouping and prerequisites
live in `Curriculum` objects holding directed acyclic graphs, of which there may
be many, overlapping, disagreeing, and drawing on the same lessons. Any curriculum
can be flattened into a sequence, and there are many valid flattenings — that is
the point, not an inconvenience.

**2. Modalities are transcodes of the text rendering by default.**
A rasterized episode is a picture *of the sentence*, not a picture of the scene
the sentence describes; a dictated episode is that same sentence spoken. Every
transcode carries the same underlying string.

This is deliberate and it is the measurement. Because the surface is provably
incidental, a system that answers correctly in one channel and not another has
learned the channel. It also makes transcoding cheap in the expensive currency:
the answer set does not change, so a lesson's floor carries over untouched and
only *fidelity* has to be re-checked — whether the rendering destroyed the
evidence the answer depends on.

One surface is **not** a transcode and is kept separate for exactly that reason.
`scene` reads the episode's structure and draws it, with the question beside it
in text; that is visual question answering, and it measures something else. It
does not inherit a floor and must be verified in its own right. The distinction
is in the code — `NATIVE_SURFACES` — not just in this file, because the two
kinds of rendering make different promises and nothing should be able to confuse
them.

**3. Responses are open-form text.**
Lessons that were multiple-choice render their options into the prompt body and
expect the answer as prose — a bare label, a label with its statement, or the
statement alone, sometimes with an instruction to emit only the label. Nothing is
graded by a model. The internal answer set is *retained* even so, because it is
what makes the floor computable, and the floor is what makes a number mean
anything.

**4. No machine-learned models anywhere in the pipeline.**
Dictation is letter-to-sound rules feeding a formant synthesizer — the way speech
was made before anything was trained. Rasterization is a bundled bitmap font and
a scanline fill. Nothing is scored by a judge. A model in the pipeline would make
the data a function of that model's weights, and the resource would stop being
reproducible by anyone who did not have them.

The cost is that the voice sounds like 1980 and the font is 5x7. Both are the
right trade: what a dictation must preserve is *which words were said*, and what
a rendering must preserve is *what the episode asked* — neither needs to be
pretty, and naturalness is not worth a dependency on somebody's weights.

**5. Vector internally, raster at the boundary.**
Exactly as text is symbolic internally (`Term`) and characters at the boundary,
images are vector internally and pixels at the boundary. The rasterizer is part
of the specification and is versioned; the reproducibility claim is "same seed
and same renderer version gives the same bytes", stated that way and not more
broadly.

Containers follow the same rule. Video is packaged as APNG, which is PNG chunks
rather than a codec, so the container is byte-exact too. Any format whose bytes
drift between encoder builds is packaging, is not hashed, and is nobody's
guarantee.

Coverage has a boundary and it is measured, not assumed. Latin diacritics are
composed from a base glyph and a mark, so most of Europe costs eleven bitmaps
rather than two hundred; Greek and Cyrillic are written out. CJK is not attempted
and will not be — it is thousands of glyphs, each needing far more than a 5x7
cell. `covers()` reports it as missing and every rasterized episode carries that
up to the caller in its fidelity record.

**6. The dataset is never enumerated.**
`(lesson, seed, presentation)` is a pure function to bytes, so any slice is
reproducible by anyone without transferring it. Object storage caches *samples*
and expensive renderings; it is not the store of record. Batches are materialized
on demand and addressed by index through a deterministic bijection, because an
infinite set cannot be shuffled.

## How internalization is measured, without a judge

**Held-out presentation.** Splits partition not only seeds but channel, language,
answer format and difficulty. Train on text and raster, evaluate on dictation;
train on three hundred languages, evaluate on a hundred unseen. Disjointness is
by construction, never by sampling.

**Compositional splits from the graph.** For any node in a curriculum, everything
upstream is the training set and the node itself is the evaluation set. That is
what the DAG is for.

**Agreement across renderings.** One instance, rendered N ways, tagged with a
shared `instance_id`: do the answers agree? This needs no gold label and no
judge. A system that internalized the structure is invariant; one that learned a
surface is not.

**The structural probe.** `Lesson.structured()` and `metadata["hidden"]` carry the
generator's own construction. Ask the system to emit the structure it recovered
and compare exactly. A system can be right for surface reasons; it cannot produce
the right *tree* for surface reasons. Hidden state must never serve as both
training signal and probe target in the same run.

## Standing constraints

* The core package has no runtime dependencies. Renderers that need them are
  optional extras, and the text path never does.
* Every lesson passes `verify` — it generates, it is deterministic, and its floor
  is low — before its data may be exported. This is a gate, not a report. When
  nothing grades the output, a silently broken generator poisons a corpus
  forever.
* Determinism is stated per channel, at the granularity it actually holds.
  Frames are hashed; containers are packaging.
* Prerequisite edges are derived from declared axes and auditable, never invented
  to make a graph look complete.
