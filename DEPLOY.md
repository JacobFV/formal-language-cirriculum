# Publishing the site to Cloudflare

The curriculum site is static: `scripts/build_site.py` renders 181 HTML pages
and a stylesheet, and a host serves them. This document covers publishing that
directory to **Cloudflare Pages** with `npx wrangler`, driven entirely from the
`Makefile` at the repository root.

The existing GitHub Pages workflow (`.github/workflows/pages.yml`) is untouched
and still publishes on every push to `master`. Retire it once Cloudflare is
proven, not before.

> This file lives at the repository root rather than in `docs/` because
> `docs/` is `.gitignore`d -- it is the default output directory of
> `scripts/build_site.py`.

---

## Quick start

```sh
make check                      # python / node / wrangler versions
make site                       # build _site/ (64 languages, ~405 MB, slow)
make preview                    # serve it locally, exactly as Pages will
make deploy                     # upload it
```

While working on the deployment itself, build something small:

```sh
make preview SAMPLES=2 LANGUAGES=english,spanish     # ~6 MB, about a second
```

`make help` lists every target and the current settings.

---

## Why Pages direct upload, and not a Worker in front of R2

Both were on the table. Pages wins on today's numbers, and the reason to reach
for R2 -- the 1 GB ceiling -- is a *GitHub* Pages limit that Cloudflare simply
does not have.

|                          | Cloudflare Pages (direct upload)   | Worker + R2                          |
| ------------------------ | ---------------------------------- | ------------------------------------ |
| Total site size          | no documented cap                  | no cap                               |
| Files                    | 20,000 free / 100,000 paid         | no cap                               |
| Per file                 | 25 MiB                             | 5 TB per object                      |
| Upload                   | one `wrangler pages deploy`, parallel, content-hashed so unchanged files are skipped | `wrangler r2 object put`, **one object per invocation** -- there is no recursive upload or sync in wrangler, so 181 files means 181 CLI runs |
| Atomicity / rollback     | each deploy is immutable, with a preview URL and one-click rollback | none; the bucket mutates in place    |
| Code to maintain         | none                               | a Worker: content types, index fallback, caching, 404s |

The site is **181 files**. Both limits that matter are file-shaped, and the
one that binds is 25 MiB per file — every lesson page inlines *every* exported
language (that is what makes the language `<select>` cost no request), so page
size grows linearly with the language count:

- measured: 64 languages x 50 samples = ~405 MB total, ~2.2 MB per page
- extrapolated: 412 languages (everything the engine speaks) x 50 samples
  = ~2.6 GB total, ~14 MB per page — **still inside the 25 MiB per-file cap**

So Pages can host the complete 412-language export, which is the whole reason
this exists. Adding the Worker and its bucket buys nothing today and costs a
component that has to be correct about MIME types.

**Switch to R2 when a single page would exceed 25 MiB.** At 50 samples that is
roughly 750 languages; at 100 samples it is roughly 375, which the engine's 412
already passes. If that day comes, the smallest change is a Worker with an R2
binding that maps `/` to `index.html`, `/x` to `x.html`, and sets
`Content-Type` from the extension — and an upload path that is not wrangler
(rclone or `aws s3 sync` against R2's S3-compatible endpoint), because
`wrangler r2 object put` uploads one object per process.

---

## Credentials

Nothing but `make deploy`, `make project` and `make whoami` needs an account.
`make site`, `make preview` and `make preflight` are entirely local.

Two environment variables:

| Variable                | What                                                                 |
| ----------------------- | -------------------------------------------------------------------- |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID, on the Cloudflare dashboard home page (also the hex string in the dashboard URL). |
| `CLOUDFLARE_API_TOKEN`  | API token, created at <https://dash.cloudflare.com/profile/api-tokens>. |

Create the token with **Create Token -> Custom token** and give it:

- **Account -> Cloudflare Pages -> Edit** (the deploy permission)
- **Account -> Account Settings -> Read** (optional; lets wrangler resolve the
  account when `CLOUDFLARE_ACCOUNT_ID` is not set)

Scope it to the one account. Nothing else is required — no Zone permissions,
no Workers Scripts, no R2.

```sh
export CLOUDFLARE_ACCOUNT_ID=...
export CLOUDFLARE_API_TOKEN=...
make whoami            # confirms which account the token resolves to
```

Interactively, `npx wrangler login` (OAuth in a browser) works instead of a
token and is the easier path for a human at a laptop. Use a token for CI.

Never put either value in the repository. `wrangler` also reads a `.env` file
if you prefer that to shell exports; keep it out of git.

---

## First-time setup

Create the Pages project once per account:

```sh
make project           # npx wrangler pages project create langcurriculum
```

This creates a Direct Upload project — Cloudflare is not connected to GitHub
and never builds anything; it only receives the finished directory. The site
then lives at `https://langcurriculum.pages.dev`.

To use a different name, set `PROJECT` everywhere (`make deploy PROJECT=...`)
and change `name` in `wrangler.toml`.

A custom domain is added in the dashboard under the project's **Custom
domains** tab. Wrangler 4.120 has no `pages domain` subcommand, so this step
is dashboard- or API-only.

---

## Deploying

```sh
make deploy                                  # production
make deploy BRANCH=trial                     # a preview URL, production untouched
make deploy SAMPLES=20 BUDGET_MB=400         # a smaller export
```

`deploy` depends on `preflight`, which depends on `site`, so one command
builds what is missing, checks it against the Pages limits (file count, and
the 25 MiB per-file cap) and refuses to upload a build that would be rejected.

Deployments are attributed to the current git commit (`--commit-hash`), which
is what makes a published page traceable to the code that produced it. Every
deploy is immutable and gets its own preview URL; the dashboard can roll
production back to any previous one.

Uploads are content-hashed, so a redeploy only transfers pages that changed.

---

## Publishing more languages

There are two ceilings, and `BUDGET_MB` only moves the second one.

**1. The database.** `make site` renders from the committed extract
(`langcurriculum/grammar/data/site-languages.db.gz`), and that extract was
itself cut at `--budget-mb 900` — it contains **66 languages and no more**.
Raising `BUDGET_MB` alone tops out there:

| `BUDGET_MB` (with the committed extract) | languages exported |
| ---------------------------------------- | ------------------ |
| 900 (default)                            | 64 — ~405 MB       |
| 2000 or higher                           | 66 — everything the extract holds |

Going past 66 needs the full database, which is ~8 GB, gitignored and built
locally. Point `DB` at it:

```sh
make deploy DB=langcurriculum/grammar/data/languages.db BUDGET_MB=5750
```

`DB` is only unpacked by the Makefile when it is the default extract; any
other path must already exist and is never written to.

For CI, cut a bigger extract instead and commit or cache it:

```sh
python scripts/build_site_db.py --budget-mb 5750 \
  --out langcurriculum/grammar/data/site-languages.db --verify
gzip -9 langcurriculum/grammar/data/site-languages.db
```

(66 languages compress to 17 MB; all 412 will be far past what belongs in a
git repository, so cache it rather than commit it.)

**2. The budget.** `build_site.py --budget-mb` estimates 1,550 bytes per
episode (180 lessons x N samples x L languages), so at the default 50 samples
each language costs about **14 MB of budget**: 900 MB buys 64 languages,
5,750 MB buys all 412. `LANGUAGES=all` skips the estimate entirely.

The estimate is conservative: real episodes average ~690 bytes, so the output
is roughly 2.2x smaller than the budget it consumed — all 412 languages at 50
samples is ~2.6 GB on disk, not 5.7 GB. Two things to keep in view when
raising it:

- **Per-page size.** Every language is inlined into every lesson page. At 412
  languages and 50 samples that is ~14 MB of HTML per page — under the 25 MiB
  Pages cap, but a heavy page for a reader on a slow link.
- **Build time.** The cost is linear in languages x samples; the full export
  is hours, not minutes, and produces gigabytes. Build it once and let the
  content-hashed upload skip the unchanged pages afterwards.

Raising `SAMPLES` multiplies both. `SAMPLES=100 LANGUAGES=all` would put every
lesson page over the 25 MiB per-file limit — `make preflight` fails before the
upload rather than after it.

---

## What Cloudflare does with the built directory

Three files in `_site/` are not lesson content:

- `_headers` — copied from `cloudflare/_headers` by `make site`. Sets
  `nosniff`, a referrer policy, and cache lifetimes (10 minutes with a day of
  `stale-while-revalidate` for lesson pages, an hour for `style.css`, which is
  not content-hashed and so cannot be `immutable`). Pages consumes this file at
  deploy time and does not serve it.
- `404.html` — copied from `cloudflare/404.html`. Without it an unknown URL
  answers **200** with the index page; with it, a real 404.
- `.nojekyll` — written by `build_site.py` for GitHub Pages. Cloudflare
  ignores it; harmless.

One behaviour worth knowing: **Pages redirects `/lessons/x.html` to
`/lessons/x`** with a 308. The site's internal links all carry `.html`, so
every navigation costs one redirect before the page (browsers cache the 308,
so it is once per URL, not once per visit). Nothing breaks; both forms serve
the same page. Removing it would mean rewriting the links inside
`build_site.py`, which this deployment deliberately does not touch.

---

## Running it from CI

Not wired up — `.github/workflows/pages.yml` is still the automated path. When
Cloudflare takes over, the job is the same three lines as a laptop:

```yaml
- run: make site
- run: make deploy
  env:
    CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

with `actions/setup-python` and `actions/setup-node` before them. Note that a
900 MB build on a hosted runner is close to its disk and time budget; a large
`BUDGET_MB` wants a self-hosted runner or a local build.

---

## Troubleshooting

| Symptom | Cause |
| ------- | ----- |
| `make site` exports only 7 languages | The database extract was not unpacked. `make site-db`, or `make distclean && make site`. |
| `Authentication error [code: 10000]` | Token missing **Cloudflare Pages -> Edit**, or `CLOUDFLARE_ACCOUNT_ID` points at a different account. |
| `Project not found` | Run `make project` once, or `PROJECT=` does not match the project's name. |
| `The Workers runtime failed to start ... newest date supported` | `compatibility_date` in `wrangler.toml` is newer than the pinned wrangler's runtime. Lower it, or raise `WRANGLER_VERSION`. |
| A file is over 25 MiB | `make preflight` names it. Lower `SAMPLES`, lower `BUDGET_MB`, or move to R2. |
