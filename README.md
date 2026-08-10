# langcurriculum

**A formal language curriculum: 180 lessons, procedurally generated, exactly graded — a generator of unbounded synthetic data for developing and evaluating symbolic AI.**

"Language ability" is not one number obtained by predicting tokens. It is a profile over
capabilities that build on each other — reference, equivalence, discrimination, sequence
memory, finite-state syntax, recursion, parsing, variable binding, unification,
quantification, compositional reference — and upward from there through causality, ontology
construction, scientific induction, proof, argument, institution design, self-modeling and
value inference.

This package is that profile, as 180 lessons you can run anything against — and, more to the point, an unbounded generator you can draw training data from. What it is *for* is stated in [INTENT.md](INTENT.md); the short version is that the question being asked is always whether a system has internalized the **structure** of a problem or only the **surface** it was shown in.

Every lesson is a **generator, not a dataset**. An episode is a pure function of a seed:
the vocabulary is invented per episode, the grammar or ontology or proof calculus is
sampled fresh, and the answer is computed from the construction rather than annotated by
anyone. Two things follow, and they are the reason the resource exists:

- **An evaluation set cannot have been trained on.** It did not exist until you asked for
  it. There is no contamination argument to have.
- **Every score has a floor.** The answer set travels with the episode, so "what does
  knowing nothing get?" is computable per lesson — and an accuracy is never reported
  without it.

Episodes are **English prose by default**. How an episode is presented — the language, the
answer format, the modality — is a parameter of the resource, not a formatting option.
Lessons themselves are **flat**: they carry no number and no section, because ordering is
the business of a `Curriculum`, of which there are several, overlapping and disagreeing.
Everything crossing the API is plain text or plain data. Point it at anything that maps a
string to a string.

Browsable curriculum, with sample episodes per lesson and a drawn view of every
curriculum's dependency graph:
**[jacobfv.github.io/formal-language-cirriculum](https://jacobfv.github.io/formal-language-cirriculum/)**

---

## Install

```bash
pip install git+https://github.com/JacobFV/formal-language-cirriculum
```

Python 3.10+. **Zero runtime dependencies** — the generators are pure Python and are
staying that way.

## Evaluate a text agent

An agent is the simplest thing that can be one: `Callable[[str], str]`.

```python
import langcurriculum as lc

lc.get("symbol_grounding").example(seed=0).prompt
```

```
In the scene: o0 is a yellow cube at (4, 8); o1 is a yellow prism at (4, 7);
o2 is a green disc at (3, 8); o3 is a blue cone at (2, 1).
Which object is the green disc?

Answer with exactly one of: o0 | o1 | o2 | o3
Reply with the answer only.
```

```python
def my_agent(prompt: str) -> str:
    return call_your_model(prompt)          # anything string -> string

report = lc.evaluate(my_agent, n=20)        # 20 fresh episodes of each of 179 lessons
print(report.table())
```

```
lesson                                n     acc   floor    lift
---------------------------------------------------------------
symbol_grounding                     20   0.950   0.325   0.926
symbol_equivalence                   20   0.900   0.300   0.857
symbol_discrimination                20   0.700   0.550   0.333
...
---------------------------------------------------------------
macro-average                        20   0.612   0.358   0.401
```

`floor` is the higher of two baselines measured on the same episodes: a uniform guesser
over each episode's own answer set, and always answering the most common gold label.
`lift` is accuracy rescaled into the headroom above that floor, so `0.0` means "no better
than not knowing" and `1.0` means perfect. **`lift` is the number to compare across
lessons**, because a yes/no lesson floors at 0.5 and a "which of these nine objects"
lesson floors at 0.11, and two lessons both scoring 0.55 are not comparable.

```python
report.lift                 # macro-average lift
report.solved               # lessons at >= 90% of the headroom
report.by_tag()             # the profile, tag by tag
report.by_capability()      # ... or by capability tag
report.by_curriculum("progressive")   # ... or as a curve along a curriculum
report["unification"].wrong # keep_wrong=N to retain failing episodes
```

Slice it: `lc.evaluate(agent, "tag:mathematics")` runs everything carrying a tag,
`lc.evaluate(agent, "core170")` runs a curriculum in its own order, `lc.evaluate(agent,
"unification,quantification")` runs named lessons, and `seed0=` picks which worlds you get.
Scoring accepts a bare answer or an answer inside a sentence, and refuses a reply that
hedges across several options; `strict=True` requires the bare answer.

Compare against the floor directly:

```python
lc.evaluate(lc.random_agent(), n=25).lift     # ~0.02 — this is what guessing looks like
```

## Generate training data

```python
import langcurriculum as lc

lc.export("train.jsonl", n=1000, seed0=0)          # 179,000 episodes
lc.export("eval.jsonl",  n=200,  seed0=1_000_000)  # disjoint worlds, by construction
```

One JSON object per line:

```json
{"lesson_id": "unification", "seed": 3, "language": "english",
 "presentation": "english/inline_bare/text", "instance_id": "9f2c1a77b0e4d310",
 "prompt": "The fact is bob is a parent of erin.\nThe pattern is B is a parent of erin.\nWhat does B unify with?\n\nAnswer with exactly one of: alice | bob | ...",
 "observation": "The fact is bob is a parent of erin.\nThe pattern is B is a parent of erin.\nWhat does B unify with?",
 "answer": "bob", "target": "bob",
 "choices": ["alice", "bob", "carol", "dave", "erin", "frank"],
 "metadata": {"level": 11, "tags": ["symbols", "grounding", "elementary-language"],
              "teaches": "...", "capabilities": [...], "axes": {...},
              "hidden": {"var": "B", "position": 0}}}
```

`prompt`/`target` is what most training pipelines want — `target` is the expected open-form
reply, which under a lettered answer format is `B` rather than `bob`. `observation` is the
question without the answer-set block, if you would rather format it yourself.
`instance_id` is shared by every rendering of the same episode, so records that differ only
in language or surface can be joined; that join is the agreement measurement.
`metadata.hidden` is the part of the world the generator knew and the agent was not shown —
the grammar it sampled, the boundary it drew, the lexicon it invented. Useful for analysis;
the one field you must not feed to a model you then intend to evaluate.

`lc.splits()` hands you non-overlapping seed ranges. Use them.

## On the command line

```bash
langcurriculum ls                                # every lesson, flat
langcurriculum ls -c progressive                 # ... in a curriculum's order
langcurriculum curricula                         # the curricula that ship
langcurriculum curricula progressive             # one, with several flattenings
langcurriculum languages                         # the languages that ship
langcurriculum surfaces                          # the modalities, and what each guarantees
langcurriculum show unification -n 3             # a lesson and some episodes
langcurriculum show quantification -L symbols    # ... in another language
langcurriculum show analogy -F labelled_label    # ... with lettered options
langcurriculum show analogy -S spoken            # ... as it would be read aloud
langcurriculum structure unification             # the episode's tree, not its rendering
langcurriculum splits -c progressive             # compositional train/eval splits
langcurriculum export train.jsonl -n 500         # a dataset
langcurriculum verify                            # re-measure every lesson's floor
langcurriculum verify -S spoken                  # ... and whether dictation keeps it answerable
langcurriculum eval mypkg.agents:answer -n 20    # evaluate module:function
langcurriculum eval random -n 25                 # evaluate the floor itself
```

---

## Languages

An episode is read in a **language**, and the default is English. This is a first-class
parameter, not a rendering flag: the lesson decides what is being asked, the language
decides what the learner reads, and the two are separate objects. Holding the language
fixed while varying the lesson measures capability; holding the lesson fixed while varying
the language measures how much of that apparent capability was memorized wording.

| code | kind | words | tier | what it is |
|---|---|---|---|---|
| `english` | natural | 342 | 1 | English prose. **The default.** |
| `spanish` | natural | 342 | 1 | Spanish: gender concord, post-nominal adjectives, ser/estar, ¿…? |
| `chinese` | natural | 342 | 1 | Mandarin: measure words, 的 modification, 吗 questions |
| `english_synonym` | natural | 342 | 1 | English whose *question* uses near-synonyms held out of training |
| `turkish` | natural | 147 + 110 | 1 | Turkish: agglutinative, verb-final, vowel harmony, evidentiality |
| `swahili` | natural | 68 + 96 | 1 | Swahili: eighteen noun classes with concord across the clause |
| `symbols` (alias `invented`) | formal | — | — | the s-expression notation the structure is built in |
| **187 more** | natural | up to 122k | 2–3 | assembled from WALS, UniMorph and Wiktionary — see below |

**Every one of them goes through the same grammar engine.** There is no template
realizer left in the codebase and no code path that treats English differently from
Swahili, which is the only way to know the engine really carries the languages it
claims to: a regression on English fails 2,200 tests immediately.

Any of the derived languages is reachable by its ISO 639-3 code:

```python
lc.get("symbol_grounding").example(0, language="deu")   # German
lc.get("symbol_grounding").example(0, language="jpn")   # Japanese
```

```python
lc.evaluate(agent, n=20)                        # English
lc.evaluate(agent, n=20, language="spanish")
lc.evaluate(agent, n=20, language="chinese")
lc.export("train.jsonl", n=1000, language="spanish")
```

```bash
langcurriculum languages
langcurriculum show symbol_grounding -L chinese
```

The same episode, in each:

```
english   In the scene: o0 is a yellow cube at (4, 8); o1 is a yellow prism at (4, 7);
          o2 is a green disc at (3, 8); o3 is a blue cone at (2, 1).
          Which object is the green disc?

spanish   En la escena: o0 es un cubo amarillo y está en (4, 8); o1 es un prisma amarillo
          y está en (4, 7); o2 es un disco verde y está en (3, 8); o3 es un cono azul y
          está en (2, 1).
          ¿Qué objeto es el disco verde?

chinese   场景中：o0是一个黄色的立方体，位于(4,8)；o1是一个黄色的棱镜，位于(4,7)；
          o2是一个绿色的圆盘，位于(3,8)；o3是一个蓝色的圆锥，位于(2,1)。
          哪个物体是绿色的圆盘？

symbols   {query: (which green disc), scene: [(obj o0 yellow cube 4 8) ...]}
```

**The answer options are rendered in the prompt's language too.** A Chinese prompt with
English options would quietly turn the task into "translate, then answer". The invariant
across languages is therefore positional: *the same option of the same episode is correct
in every language*, which is what the test suite asserts. The one exception is an answer
set the pack does not know as a whole — object ids, nonce forms, or the inflected English
forms that a morphology lesson is *about* — which stays in the source tokens and says so
in `metadata["untranslated_options"]`, because a prompt whose options are visibly in
another language is a much smaller problem than a prompt with two identical options.

### What each pack implements

Every pack states this in `grammar_notes`, and the site prints it.

**Spanish** — gender and number agreement on articles and adjectives (`un cubo rojo`,
`una esfera roja`, `las esferas rojas`); adjectives after the noun; `ser` for identity and
`estar` for location; inverted opening question marks; `y`→`e` before *i-*/*hi-* and
`o`→`u` before *o-*/*ho-*; plural from the vocabulary with a regular `-s`/`-es` fallback;
and the `el agua` exception, where a feminine noun with a stressed initial /a/ takes the
masculine article while its adjectives still agree as feminine. *Not attempted:*
subjunctive, clitic pronouns, agreement across a relative clause.

**Chinese** — no inflection anywhere; measure words for counting and pointing (`三本书`,
`这个立方体`, `一把铲子`), per-noun, with `个` as the deliberate fallback; `的` for
adjectival modification, recorded per adjective so that `红色的立方体` links and `大立方体`
does not; topic–comment framing of each section; questions by particle (`吗`) and in-situ
wh-words, never by inversion; the enumerating comma `、` for items but `；` between
clauses; no spaces and full-width punctuation throughout. *Not attempted:* 把/被
constructions, resultative complements, the 是…的 cleft, numeral-to-character conversion.

**Both** translate a coined identifier when it happens to equal a word they know — a causal
variable named `big` reads as `grande` / `大`. The renaming is consistent within an episode,
so nothing becomes ambiguous, and a test asserts that two distinct identifiers never render
as one string. It is a cosmetic oddity, not a correctness one, and it is left alone because
the alternative — deciding which occurrences of a word are "really" that word — is exactly
the guess these packs avoid.

### Vocabulary

Each natural pack ships **321 typed open-class entries** as package data — the whole of
the vocabulary the curriculum's generators actually coin — with the morphology that
language needs:

| | nouns | adjectives | verbs | names | other |
|---|---|---|---|---|---|
| english | 119 | 30 | 39 | 25 | 108 |
| spanish | 137 (gender + plural) | 27 (4 agreement forms each) | 37 (inf/3sg/3pl/pret) | 47 | 73 |
| chinese | 102 (+ measure word) | 30 (+ 的 attachment) | 40 (+ aspect) | 54 | 95 |

Spanish and Chinese additionally carry **248 field lead-ins**, **475 / 440 predicate
phrasings**, and **179 question templates** each, plus around 25 agreement-aware template
functions per pack for the phrases that need the source words rather than their rendering.
Weighted by how often each structure actually appears, that covers **100% of section
lead-ins, ~90% of predicates and ~99% of questions**. Everything beyond it falls back to a
labelled row carrying the source identifier — visibly a gap rather than invented grammar.
Zero runtime dependencies: it is JSON, loaded lazily, no model and no download.

### Adding a language

A pack is three things: a `Vocabulary` (the JSON above), a `Lexicon` (closed class,
typography, lead-ins, templates), and a realizer that overrides only the **strategies**
where its language differs — `noun_phrase`, `relational`, `attributive`, `labelled`,
`enumerated`, `field_sentence`, `question`, `join_words`, `join_list`, `join_clauses`,
`sentence`. Nothing in the shared walk assumes SVO order, suffix pluralization, article
selection by phonology, or questions formed by inversion; those are English's answers to
questions the strategies ask, and Chinese overrides almost all of them.

```python
from langcurriculum.languages import Lexicon, NaturalLanguage, register_language

register_language(NaturalLanguage(code="french", name="French", lexicon=FRENCH))
```

Templates may be format strings over rendered arguments, or callables
`fn(language, terms) -> str` when a phrase needs the source words — which is what
agreement requires. **A template with fewer slots than the structure has arguments is
rejected** in favour of the generic question, so a pack cannot lose information by being
written in a hurry; that rule is what took Spanish from 18 dropped query arguments to zero
and Chinese from 33 to zero.

### The grammar engine

The template design above scales to three languages and stops. Templates encode word
order in their **slot positions**, and vocabularies encode morphology as **stored forms**;
neither survives a verb-final language, an agglutinative one, or one with eighteen noun
classes. `langcurriculum.grammar` is the replacement, and `turkish` and `swahili` are
generated by it.

It is a generative grammar in the unification tradition — the branch that scaled, not the
transformational one. Five modules:

| module | what it is |
|---|---|
| `features` | feature structures and unification — **one** mechanism for Spanish gender, Chinese classifiers, Turkish harmony and Bantu concord |
| `category` | the category inventory. Noun **class** rather than gender, semantic **role** rather than argument position |
| `morphology` | paradigm slots, an ordered phonological layer, and the four kinds of morphology: isolating, stored, concatenative, templatic |
| `syntax` | **18 constructions**, language-neutral — what an episode compiles to before a language is chosen |
| `linearize` | one walk, parameterized by word order, alignment and concord |

The two design choices that do the work are both about generality. **Noun class, not
gender**: Spanish masculine is the value `"m"` of the same feature whose values in Swahili
are `"1"`…`"18"`, so Bantu concord needs no parallel mechanism. **Role, not position**: an
argument arrives labelled `agent` or `patient`, which is what lets a grammar decide for
itself that an agent is preverbal and unmarked (Turkish), suffixed with `が` (Japanese), or
ergative when the clause is transitive (Basque). A positional slot can express none of
those.

The honest measure of whether the parameterization works is the **override count** — how
much of a language the parameters cannot say:

| grammar | overrides | what they are |
|---|---|---|
| `english` | 4 | `a`/`an` phonology; auxiliary fronting; negation on the auxiliary; wh-copula |
| `turkish` | 4 | the `mI` clitic; double-marked possession; locative case; differential object marking |
| `swahili` | 3 | class concord prefixes; the class-pair plural; the nasal allomorph |

**Turkish** is the forcing function, chosen because it breaks five assumptions at once:
stored forms die (a noun has hundreds of cells, and the data file stores *one* — the stem),
positional templates die (verb-final, case-marked), the gender enum dies by being unused,
the copula dies (`küp kırmızı`, no word for "is"), and question formation is a clitic that
harmonizes with whatever the sentence happened to end with. Morphology is
archiphonemic — the plural is `lAr`, the accusative `(y)I` — resolved **cyclically** at each
seam, because `ev-ler-i-mi-z-de` harmonizes left to right and any other order gets it wrong.

**Swahili** proves the concord layer generalizes: the plural is a *class change* rather
than a suffix (`kitabu`→`vitabu`, `mtu`→`watu`, `nyumba`→`nyumba`), concord reaches the
adjective and the verb, the prefix has a pre-vocalic allomorph (`kitabu kikubwa` but
`kitabu chekundu`), the class 9/10 nasal has three outcomes depending on the following
consonant, and borrowed adjectives take no concord at all.

Coverage is **declared, not assumed**. Both new packs ship a partial vocabulary — Turkish
~120 entries, Swahili ~75, against ~321 for the original three — so a word the grammar does
not know passes through in English. That is a visible gap rather than a silent mistranslation,
it is flagged by `partial_vocabulary`, and it is asserted by the test suite. What is *not*
partial is the grammar: all 179 implemented lessons render in both languages.

### The language database

Hand-writing a grammar per language stops at three. The engine's parameters are
the axes **WALS** already codes, its morphology is what **UniMorph** already records,
and its lexicon is what **Wiktionary** already lists — so beyond the hand-written
grammars, a language is *assembled from data*:

| source | licence | what it supplies | scale |
|---|---|---|---|
| [WALS](https://wals.info) (Dryer & Haspelmath 2013) | CC-BY 4.0 | word order, alignment, articles, concord, classifiers | 2,442 languages coded |
| [Grambank](https://grambank.clld.org) (Skirgård et al. 2023) | CC-BY 4.0 | denser coding where WALS has gaps | — |
| [UniMorph 4.0](https://unimorph.github.io) (Batsuren et al.) | CC-BY-SA | inflected forms with feature bundles | **13,019,355 forms**, 170 languages |
| [Wiktextract](https://kaikki.org) (Ylonen 2022) | CC-BY-SA | translation tables | **3,086,943 senses**, 155k English entries |
| Wiktextract, per-language | CC-BY-SA | inflection tables — the paradigms UniMorph omits | **43,701,065 forms**, 28 languages |

```bash
python scripts/fetch_unimorph.py --raw <dir>
python scripts/build_langdb.py  --raw <dir> --fetch --all-words
python scripts/load_wiktionary_forms.py --raw <dir> --db <database>
```

Three commands, not one. The first fetches the paradigms — the build tells you
to and cannot do it itself. The last adds the per-language inflection tables in
the fourth row above: forty-three of the fifty-seven million forms, and without
it the build finishes, works, and has UniMorph-only morphology. Running only the
middle command produces a two-gigabyte database rather than an eight-gigabyte
one, which is the sort of difference that is easy not to notice.

Builds an 8 GB SQLite database — stdlib `sqlite3`, so **still zero runtime
dependencies**, indexed so a lookup is a B-tree descent, and lazy so a process
rendering Turkish reads no Finnish. It is *not* committed: it is reproducible
from the cited sources, and eight gigabytes of binary does not belong in git.

**A hand-written grammar draws on the database for the words it lacks.** Curated
entries win and the database only fills gaps, under two rules that exist to keep an
episode answerable. The import is restricted to vocabulary the curriculum actually
coins, so a minted identifier is never looked up — Spanish was rendering the nonce `nu`
as `ni`, which is also what the nonce `ni` became. And an imported form is dropped
wherever it would **collide**, with another import or with a curated entry: Turkish
*para* is both *money* and *coin*, Swahili *sanduku* both *crate* and *box*, and an
episode naming both would be unanswerable. A visibly untranslated word is a much smaller
problem than an ambiguous one. This took Turkish from 115 curriculum keys to 246 and
Swahili from 50 to 157, without touching a single verified entry.

**Coverage, measured rather than claimed.** Of the curriculum's 403 keys, 269 are
dictionary words and 134 are coined identifiers (`kb_fact`, `astar`, `dola`) that
must pass through untranslated in every language. Against the 269:

| lexical coverage | languages |
|---|---|
| ≥ 80% | **22** |
| ≥ 60% | **55** |
| ≥ 40% | **83** |
| ≥ 20% | **146** |

German 95%, Spanish 94%, French 94%, Russian 93%. **187 languages** carry enough
real lexical data to be worth presenting (tier 2–3); the rest have typology only.

**Tiers are checked, not asserted.** A language declares what backs it and the
test suite verifies the claim against row counts:

| tier | backed by | count | verified by a speaker? |
|---|---|---|---|
| 1 | hand-written grammar, curated lexicon, real phonology | 6 | yes |
| 2 | derived grammar, imported lexicon **and** morphology | 88 | **no** |
| 3 | derived grammar, imported lexicon, no morphology | 312 | **no** |
| 4 | typology only — no lexicon | 4,722 | not registered |

**Two morphology sources, never mixed.** UniMorph is a paradigm resource with a fixed
schema and is what the inducer learns from. It has one systematic gap and it is exactly
the one that hurts: **suppletive auxiliaries are absent**. German `ist`, Russian `есть`,
Italian `è` and Polish `jest` do not appear in their own UniMorph files, though each runs
to hundreds of thousands of forms — a copula does not have a paradigm so much as a list.
Wiktionary's inflection tables have the list (`sein` carries 113 tagged forms), so they
are harvested as a second source. The two are **never pooled for induction**: two
annotation schemes behind one cell key halved held-out accuracy on Finnish and Turkish the
moment the second source arrived, so the inducer takes UniMorph where it exists and
Wiktionary where it does not.

**The copula is identified with no per-language table anywhere.** Wiktionary lists several
verbs under *be* with nothing to separate them — German *werden* beside *sein*, Italian
*venire* beside *essere*, Czech *mít* beside *být*. Three signals do it, and all three are
facts about frequency rather than about any particular language: the copula has the
**shortest** finite form (Zipf), it is the most **suppletive** (sharing almost nothing
with its own infinitive), and where those tie the dictionary's **primary sense** decides.
That is 17 of the 20 languages checked exactly right — `ist`, `è`, `есть`, `είναι`, `är`,
`je`, `van`, `on`, `yra` — with Polish and Ukrainian left as infinitives because their
Wiktionary entries carry no conjugation table, which `gaps()` reports.

**Morphology is induced, not authored.** For the 171 UniMorph languages, an
attested cell is used directly; for a lemma UniMorph never listed, the inflector
applies the transformation that lemmas *ending the same way* undergo. Indexing on
the stem's final characters is what recovers Turkish vowel harmony, Finnish
gradation and German umlaut **without being told any of them exist** — a test
asserts that the inducer produces *evler* and *kitaplar* having never heard of
harmony. Accuracy is measured on held-out paradigm cells, not spot-checked.

**Articles and the copula are also derived, not authored.** Wiktionary tags *der*
masculine and *das* neuter, so the paradigm that tells `das Buch` from `der Buch` is
already in the data — no per-language article table is written anywhere. The copula is
picked from the candidates Wiktionary lists under *be* — German *werden* beside *sein*,
Italian *venire* beside *essere* — by three signals, all facts about frequency rather
than about any particular language: it has the **shortest** finite form (Zipf), it is
the most **suppletive** (sharing almost nothing with its own infinitive, as *být*/*je*
does and *mít*/*má* does not), and where those tie the dictionary's **primary sense**
decides. Seventeen of twenty languages checked come out exactly right — `ist`, `è`,
`есть`, `είναι`, `är`, `je`, `van`, `on`, `yra`.

**No language may silently lose a distinction.** `deformalization` hands a learner four
quantified glosses and asks which matches a formula; if two render alike the episode is
not clumsy but **unanswerable**, and it fails invisibly, because a missing negator looks
like a positive sentence rather than an error. French did exactly that — its dictionary
lists the discontinuous *ne … pas* first, no single slot could hold it, and *every prism
is yellow* and *no prism is yellow* came out identical. A negator is now never empty
(the dedicated word, else the negative determiner, else the English word), and a test
asserts that all **411 registered languages** keep the four claims apart.

**What derived grammars still get wrong.** Section headings are the translated noun
rather than an idiomatic lead-in — `Szene:`, not `In der Szene:`. French gets `la eau`
rather than `l'eau`, because elision is a phonological rule nobody has written for it.
Polish and Ukrainian copulas stay as infinitives, their Wiktionary entries carrying no
conjugation table. Each gap is listed by `DerivedGrammar.gaps()` and none is hidden
behind a plausible default.

### Why `english_synonym` exists

It is a **held-out-vocabulary test**. The body of the episode keeps the words a model was
trained on and only the *question* switches to a synonym it has never read — `red` becomes
`crimson`, `cube` becomes `block`. Substituting in both places would make the episode
*easier* than the default, which is why the substitution is asymmetric.

### Why the `symbols` notation is still here

It is exact, it is short, and it is the raw view of a lesson's coinages. It is registered
under the alias `invented` because it is where per-episode invented vocabulary is seen
unadorned — but note what that does and does not mean:

**Invented vocabulary is a property of the lessons, not of the notation.** `lexicon_induction`
coins three new words per episode and grounds them in support examples; `theorem_proving`
invents a proof calculus with freshly-named rules. Those coinages reach every language —
*"词表如下：ppk说橙色、tks说紫色和mzp说黄色。… 请找出tks对应的物体。"* — because a coined
word is the same coined word in any language. That is the point: nothing carries over
between episodes except the ability.

## What is in it

180 lessons, flat. They used to be 170 numbered ones across 17 sections plus 10
supplementary; that ordering still exists, but as a *curriculum* rather than as a property
of the lessons:

| curriculum | nodes | edges | what it claims |
|---|---|---|---|
| `canonical` | 180 | 0 | every lesson in the order the package used to declare them |
| `core170` | 170 | 0 | the original numbered sequence, exactly |
| `supplementary` | 10 | 0 | the lessons that sat outside that sequence |
| `everything` | 180 | 0 | alphabetical — the null opinion |
| `progressive` | 180 | 249 | edges **derived** from the declared difficulty axes |
| `tag:<name>` | — | 0 | built on demand from what lessons declare |
| `capability:<name>` | — | 0 | built on demand from what lessons declare |

Only `progressive` has edges, and they are derived rather than authored: `X → Y` when Y is
at least as demanding as X on every declared axis and strictly more on one, and the two
share a tag or capability. Hand-writing 169 prerequisites would have been inventing
structure nobody measured. A derived relation is auditable, and wrong in ways someone can
point at.

Every lesson declares its level, its tags, its capability tags, and its position on
eight difficulty axes — `lexical_novelty`, `grammar_complexity`, `recursion_depth`,
`compositional_depth`, `discourse_horizon`, `world_complexity`, `ambiguity`,
`reasoning_depth` — so a result is a profile rather than a single score.

### Coverage, honestly

- **170** lessons in `core170`. All 170 are in the registry, in **5 hand-written
  languages** — English, Spanish, Chinese, Turkish, Swahili — plus a held-out-
  vocabulary English variant, and any of **411 more** assembled from the database.
- **169** of them generate episodes. **1** — `open_world_research_agent` — is
  `status="spec"` and deliberately raises rather than pretending. Its content is a *loop*
  (discover an ontology, theorize, design an experiment, run it, revise under criticism,
  report with provenance) whose score is a trajectory functional, not a function of one
  answer. A single-step version would grade something easier while wearing this name. The
  full reasoning is on the class as `note`, and it stays in the registry so the gap is
  visible rather than quietly absent.
- **180** lessons registered in total: the 170 plus 10 supplementary ones (palindromes,
  string reversal, center embedding, comparatives, negation, set operations, and friends)
  that fill in the syntax and semantics ladder without being part of the numbered sequence.
- **179** implemented lessons, each verified to generate, to be deterministic, and to have
  a beatable floor. See "Verification" below.
- **177** of those 179 take a difficulty. The **2** that do not — `spatial_language` and
  `ontology_alignment` — say so through `supports_difficulty()`, and the reason is in each
  case that the structure is pinned by what makes the lesson work at all: one object per
  compass direction, and a 3-bit lattice.
- **6** surfaces an episode can be rendered into, **5** of them transcodes of the same
  string and **1** (`scene`) a native drawing of the episode's structure.
- Two lessons carry names that differ from an earlier written specification:
  `parse_depth` was `parse-tree`, and `entailment` was `semantic-entailment`.

## One file, one class, one lesson

```
langcurriculum/
  lesson.py         Lesson, Example — what a lesson is and what an episode looks like
  registry.py       lesson id -> class, plus tag / capability views. No ordering.
  context.py        what a generator is told: language, difficulty
  presentation.py   language x answer format x surface — how an episode is shown
  address.py        (lesson, seed, difficulty, presentation) -> bytes, and batch sampling
  curricula/
    graph.py        Curriculum, Node, linearize, layers, frontier, train_eval_split
    core170.py      the orderings the package used to have, preserved exactly
  surfaces/         the modalities an episode's text can be carried in
    content.py      Content, Asset, Fidelity
    font.py         a 5x7 bitmap font, so rasterizing needs nothing installed
    raster.py       text -> PNG, deterministic, zero dependencies
    spoken.py       text -> the transcript a dictation is read from
    video.py        text -> a sequence of frames
  languages/        the registry, the shared realizer, and one module per pack
    base.py         Lexicon + the strategies a pack overrides
    lexicon.py      typed Vocabulary (gender, plural, classifier, agreement forms)
    symbols.py      the s-expression notation
  grammar/          the unification grammar engine and the language database
  evaluate.py       evaluate(), Report, LessonResult, floors and reference agents
  dataset.py        JSONL export, seed / presentation / compositional splits
  scoring.py        text reply -> score, without a second model to grade the first
  verify.py         the admission test a lesson has to pass, per lesson and per surface
  cli.py            langcurriculum ls | curricula | show | structure | export | verify | eval
  _structure.py     the internal representation (private; never crosses the API)
  generators/       shared generator machinery, grouped by the worlds it builds
  lessons/          180 modules, flat
    symbol_grounding.py           -> class SymbolGrounding
    symbol_equivalence.py         -> class SymbolEquivalence
    ...
```

Each lesson module holds its generator and one class:

```python
class Unification(Lesson):
    """Structural symbolic matching."""

    id = "unification"
    level = 11
    tags = ("symbols", "grounding", "elementary-language")
    teaches = "structural symbolic matching"
    capabilities = ()
    axes = {"compositional_depth": 3, "reasoning_depth": 3}

    generate = staticmethod(gen_unification)
```

There is no `number` and no `section`. A lesson that declared its own position would be a
second source of truth about ordering, and it would eventually disagree with the first;
a test asserts that none of them do.

The registry is explicit — every class is imported by name — so what is in the curriculum
is a fact you can read off the source tree, not the result of a directory scan that might
quietly skip a file that failed to import. A test checks the declared list against the
directory, so a module can be neither silently skipped nor silently unlisted.

## Curricula

```python
>>> import langcurriculum as lc
>>> c = lc.curriculum("progressive")
>>> c
<Curriculum progressive: 180 nodes, 249 edges>
>>> [n.lesson for n in c.linearize()][:3]
['ambiguity_preservation', 'analogy', 'anytime_reasoning']
>>> len({tuple(n.key for n in o) for o in c.linearizations(6)})   # many valid orders
6
>>> train, ev = c.train_eval_split("unification")   # everything upstream trains
```

A curriculum is a DAG over lessons. Several may draw on the same lessons and order them
differently, which is the point — there was never one true order, and writing one onto the
material made that impossible to say. Two things follow that a list cannot give you:

- **Many flattenings.** `linearize()` returns a canonical one (the site and the samples
  have to be reproducible); `linearizations()` enumerates alternatives, and every one of
  them respects every edge.
- **Compositional splits.** For any node, everything upstream is a training set and the
  node itself is held out. The graph *is* a generator of compositional-generalization
  tests — `lc.dataset.compositional_splits("progressive")`.

## Presentation, and other modalities

```python
>>> lc.get("analogy").example(0, presentation="english/labelled_label").target
'C'
>>> lc.get("analogy").example(0, presentation="spanish/labelled_label").target
'C'
>>> from langcurriculum.surfaces import transcode_example
>>> transcode_example(lc.get("analogy").example(0), "raster")
<Content raster 300 chars, 1 assets, 1556B>
```

Replies are **open-form text**. Lessons that were multiple-choice write their options into
the prompt body, and the answer format decides whether the expected reply reads `B`,
`B: the red cube`, or `the red cube`. The answer set is still retained, because it is what
makes the floor computable.

The other surfaces are **transcodes**: a rasterized episode is a picture *of the sentence*,
not a picture of the scene the sentence describes, and a dictated one is that same sentence
read aloud. This is deliberate. Because the surface provably carries the same string, a
system that answers correctly through one and not another has learned the surface — which
is the measurement. Everything is procedural and rule-based; there is no model anywhere in
the pipeline.

| surface | kind | what it produces | reproducibility |
|---|---|---|---|
| `text` | transcode | the string | exact, given the language database version |
| `raster` | transcode | 8-bit greyscale PNG, bundled 5x7 font | exact, given `raster_v2` and the font |
| `spoken` | transcode | the transcript a dictation is read from | exact; rule-based |
| `audio` | transcode | a WAV, from letter-to-sound rules into a formant synthesizer | exact; no model, no host voice |
| `video` | transcode | PNG frames, packaged as APNG | exact, frames *and* container |
| `scene` | **native** | a picture of the scene, question beside it in text | exact; procedural, no blending |

Transcoding does not change the answer set, so a lesson's floor carries over untouched.
What a transcode *can* do is destroy the evidence — draw a glyph the font lacks, or read
two distinct options as the same sound — and `verify -S <surface>` measures exactly that,
by rendering real episodes rather than by declaring compatibility in a table.

`scene` is the exception and is kept apart in the code (`NATIVE_SURFACES`), because it
reads the episode's *structure* and draws it rather than re-presenting a sentence. That is
visual question answering: the ground truth is still computed from the construction, but
the floor does **not** carry over and has to be re-measured.

Everything is zero-dependency and procedural. The PNG writer is `struct` and `zlib`; the
animation is APNG, chosen because it is PNG chunks rather than a codec and therefore
byte-exact where an mp4 would not be; the voice is a source-filter synthesizer with three
resonators, the way speech was made before anything was trained.

Font coverage is measured rather than assumed. Latin diacritics are *composed* — `é` is
the `e` this font has plus an acute drawn in the leading — so most of Europe costs eleven
mark bitmaps instead of two hundred glyphs. Greek and Cyrillic are written out. CJK is not
attempted, and `covers()` says so rather than drawing boxes quietly.

## Difficulty

Eighteen lessons with an obvious structural knob accept a difficulty in `[0, 1]`, which
scales scene size, recursion depth, sequence length or distractor count. `ls` marks them
with `~`, and `Lesson.supports_difficulty()` answers it honestly for the rest — a knob that
is accepted and ignored would be worse than none.

With no difficulty given, a lesson generates exactly what it always did. That is enforced:
the retrofit was checked episode-by-episode against output captured beforehand.

## Verification

A lesson is only evidence if its floors are right. Two generator bugs in this curriculum's
history produced fake competence — object-id order correlated with the answer, and
referring expressions that did not uniquely refer — and both would have looked like an
agent "solving" a lesson it had not. So every lesson must demonstrate, over a block of
freshly generated episodes:

1. **it generates** — no exceptions across the block;
2. **it is deterministic** — the same seed gives the same episode, every time;
3. **its floor is low** — always answering the most common gold label scores near chance,
   not near one.

```bash
langcurriculum verify                 # 179/179 passed
```

All 179 implemented lessons pass. The threshold is 0.60 for binary lessons and 0.45
otherwise, and a lesson that trips it is re-measured over a larger block before being
condemned, because a constant guesser's score is itself a random variable.

## The committed samples

`data/samples/` holds 100 episodes per lesson in every registered language — 89,500
records — from seeds 0–99, with a `manifest.json` carrying every lesson's declared metadata
and measured floors. The static site under `docs/` renders all of it, English first.

These are a **published sample, not the resource**. The resource is the generators, and
every byte here can be rebuilt:

```bash
python scripts/build_samples.py       # data/samples/
python scripts/build_site.py          # docs/
```

Do not train on seeds 0–99 and then evaluate on them. Use `lc.splits()`.

## Design notes

**Why generators rather than a corpus.** A tagged corpus fixes the vocabulary, and a
capability measured over a fixed vocabulary is inseparable from having memorized that
vocabulary. Here a lesson like `lexicon_induction` invents three new words per episode and
grounds them in support examples; a learner that memorized a vocabulary learns nothing from
it. Nothing carries over between episodes except the ability.

**Why the language is a parameter and not a format.** The curriculum is about language, so
"which language is this in?" is a question the resource has to be able to answer, and to
answer differently for the same lesson. Making it a pack rather than a flag means the
answer can grow: the generators build structures and compute answers, and 471 distinct
predicate heads are rendered by a handful of general rules plus a table of words. That is
also why English is an entry in a registry rather than the special case — the day there is
a second language, nothing about the lessons has to move.

**Why the answer set travels with the episode.** Grading free text against an exact answer
is where benchmarks leak. Because each episode carries a small closed set of legal answers,
"did the reply name the right one?" is decidable — no second model grades the first, and no
regex has to guess what the model meant.

**Why the hidden state is separated.** Each generator returns the world it built alongside
the question. The evaluator can read it; the agent never sees it. That is what makes the
ground truth exact instead of annotated: `quantification` chooses the truth value *first*
and builds a scene to match, because sampling a scene and reading off the truth value makes
most quantified statements false and lets a constant "no" score 0.73.

## What this is for

The long answer is [INTENT.md](INTENT.md). The short one:

The curriculum exists to **autonomously develop and evaluate symbolic AI** — to supply
unbounded synthetic problems of rising compositional complexity, and to measure whether a
system has internalized the structure of a problem or only the surface it was shown in.

Four measurements follow from that, and none of them needs a judge:

- **Held-out presentation.** `dataset.held_out()` partitions any presentation axis. Train
  on text and raster, evaluate on dictation; train on three hundred languages, evaluate on
  a hundred unseen. Disjointness is by construction, never by sampling.
- **Compositional splits.** `Curriculum.train_eval_split(node)` — everything upstream
  trains, the node is held out.
- **Agreement across renderings.** Every record carries an `instance_id` shared by every
  presentation of the same episode. Ask whether the answers agree. No gold label required;
  a system that internalized the structure is invariant, one that learned a surface is not.
- **The structural probe.** `Lesson.structured()` and `metadata["hidden"]` carry the
  generator's own construction — the tree, the grammar, the graph. Compare a recovered
  structure against it exactly. A system can be right about the answer for surface reasons;
  it cannot produce the right *tree* for surface reasons.

Standing constraints, in case a future change is tempting: no machine-learned model
anywhere in the pipeline; the core has no runtime dependencies; the dataset is never
enumerated — `(lesson, seed, difficulty, presentation)` is a pure function to bytes, so
object storage is a cache and not the store of record.

## Drawing data without enumerating it

```python
>>> from langcurriculum.address import Space, batch
>>> space = Space(lessons=tuple(lc.lesson_ids()), seeds=(0, 10**6))
>>> len(space)
180000000
>>> [a.key() for a in batch(space, 0, 2)]
['...', '...']
```

An infinite set cannot be shuffled, so a batch index is mapped to an address through a
keyed bijection — a small Feistel network with cycle-walking. Batches are reproducible from
their index alone, and two batches that do not share indices cannot share episodes.

### Caching what is expensive

```python
>>> from langcurriculum import CachedRenderer, store_from_env
>>> renderer = CachedRenderer(store_from_env())       # None if nothing is configured
>>> renderer.warm(batch(space, 0, 1000))
{'hits': 0, 'misses': 1000, 'skipped': 0}
```

Object storage here is a **cache, not the store of record** — nothing is ever only in the
bucket, so a miss costs a re-render and never an episode. Two rules keep it from going
stale, and both are enforced in code rather than left to the caller: the renderer version
is part of the cache key, and cheap surfaces are never cached at all, because regenerating
a text episode costs less than asking whether it is cached.

`LocalStore` is a directory. `S3Store` speaks the S3 API with SigV4 signed by hand — a page
of `hmac` and `hashlib` rather than a dependency — so Cloudflare R2 works out of the box:

```bash
export R2_ACCOUNT_ID=... R2_BUCKET=... R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=...
```

## License

MIT. See [LICENSE](LICENSE).
