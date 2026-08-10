# Build the curriculum site and publish it to Cloudflare Pages.
#
#   make site       build the static site into _site/
#   make preview    serve _site/ locally the way Cloudflare will serve it
#   make deploy     upload _site/ to the Cloudflare Pages project
#   make clean      remove the build output
#
# Nothing here needs a Cloudflare account except `deploy`, `whoami` and
# `project`. Wrangler is always run through `npx` -- there is no global
# install to keep in sync, and WRANGLER_VERSION below pins what runs.
#
# Credentials, first-time project creation and the choice of Pages over
# R2 are documented in DEPLOY.md.
#
# The GitHub Pages workflow (.github/workflows/pages.yml) still works and is
# untouched; this is a second, independent way to publish the same bytes.

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ---------------------------------------------------------------- parameters

# Where the site is built. Also `pages_build_output_dir` in wrangler.toml --
# change both together.
OUT ?= _site

# Scratch space for the unpacked language database and the parameter stamp.
BUILD ?= .build

# Episodes per lesson per language, and the size at which build_site.py stops
# adding languages. 900 MB is what GitHub Pages could hold (64 languages);
# Cloudflare has no such cap -- see "Publishing more languages" in DEPLOY.md.
SAMPLES ?= 50
BUDGET_MB ?= 900

# Comma-separated language codes. Empty means "whatever fits BUDGET_MB".
# Handy while working on the deployment itself:
#   make preview SAMPLES=2 LANGUAGES=english,spanish
LANGUAGES ?=

# The Cloudflare Pages project and the branch deployments are attributed to.
# A deployment to PRODUCTION_BRANCH is the live site; any other branch name
# gets its own preview URL.
PROJECT ?= langcurriculum
PRODUCTION_BRANCH ?= main
BRANCH ?= $(PRODUCTION_BRANCH)

WRANGLER_VERSION ?= 4.120.0
WRANGLER ?= npx --yes wrangler@$(WRANGLER_VERSION)

PYTHON ?= $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3)

# Cloudflare Pages limits, checked before every deploy.
# https://developers.cloudflare.com/pages/platform/limits/
MAX_FILES := 20000
MAX_FILE_BYTES := 26214400

# ------------------------------------------------------------------- sources

DB_GZ := langcurriculum/grammar/data/site-languages.db.gz
EXTRACT := $(BUILD)/site-languages.db

# The database the site is rendered from. The committed extract holds 66
# languages, which is the ceiling for anything built here; to publish more,
# point this at the full (gitignored, ~8 GB) database and raise BUDGET_MB:
#   make site DB=langcurriculum/grammar/data/languages.db BUDGET_MB=5750
# Only the extract has a rule to build it -- an overridden DB must already
# exist, and is never written to.
DB ?= $(EXTRACT)

STAMP := $(BUILD)/params
INDEX := $(OUT)/index.html

SOURCES := scripts/build_site.py scripts/serve_site.py \
           $(shell find langcurriculum -name '*.py' 2>/dev/null)

# Cloudflare-only files build_site.py knows nothing about, copied into the
# deployment after the build: header rules and a real 404 page.
EXTRAS := cloudflare/_headers cloudflare/404.html

BUILD_ARGS := --out $(OUT) --samples $(SAMPLES) --budget-mb $(BUDGET_MB) \
              $(if $(LANGUAGES),--languages $(LANGUAGES),)

COMMIT := $(shell git rev-parse HEAD 2>/dev/null)

# ------------------------------------------------------------------- targets

.PHONY: help site site-db preview deploy preflight project whoami check \
        clean clean-db distclean FORCE

help: ## show this help
	@echo "targets:"
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk -F':.*?## ' '{printf "  \033[1m%-12s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "settings (make VAR=value):"
	@echo "  OUT=$(OUT)  SAMPLES=$(SAMPLES)  BUDGET_MB=$(BUDGET_MB)  LANGUAGES=$(if $(LANGUAGES),$(LANGUAGES),<fit BUDGET_MB>)"
	@echo "  PROJECT=$(PROJECT)  BRANCH=$(BRANCH)"
	@echo "  DB=$(DB)  PYTHON=$(PYTHON)"

# Unpack the 17 MB committed extract (77 MB unpacked). Without a database the
# registry falls back to the seven hand-written packs and only 7 languages
# build; with the extract, 64 fit in the default budget and 66 exist.
$(EXTRACT): $(DB_GZ)
	@mkdir -p $(BUILD)
	gunzip -c $< > $@.tmp && mv $@.tmp $@
	@ls -l $@

site-db: $(EXTRACT) ## unpack the language database extract

# Rewritten only when the build parameters actually change, so changing
# SAMPLES or LANGUAGES forces a rebuild and re-running `make site` does not.
$(STAMP): FORCE
	@mkdir -p $(BUILD)
	@test "$$(cat $@ 2>/dev/null)" = "$(BUILD_ARGS)" || echo "$(BUILD_ARGS)" > $@

FORCE:

$(INDEX): $(DB) $(STAMP) $(SOURCES) $(EXTRAS)
	LANGCURRICULUM_DB=$(abspath $(DB)) $(PYTHON) scripts/build_site.py $(BUILD_ARGS)
	cp $(EXTRAS) $(OUT)/
	@echo "pages: $$(find $(OUT) -name '*.html' | wc -l)  size: $$(du -sh $(OUT) | cut -f1)"

site: $(INDEX) ## build the static site into OUT (default _site)

preflight: site ## check the build against Cloudflare Pages limits
	@n=$$(find $(OUT) -type f | wc -l); \
	  if [ "$$n" -gt $(MAX_FILES) ]; then \
	    echo "$(OUT): $$n files, over the $(MAX_FILES)-file Pages limit" >&2; exit 1; fi; \
	  echo "files: $$n / $(MAX_FILES)"
	@big=$$(find $(OUT) -type f -printf '%s\t%p\n' | awk -F'\t' '$$1 > $(MAX_FILE_BYTES)'); \
	  if [ -n "$$big" ]; then \
	    echo "over the per-file Pages limit ($(MAX_FILE_BYTES) bytes, 25 MiB):" >&2; \
	    echo "$$big" >&2; \
	    echo "lower SAMPLES or BUDGET_MB, or move to R2 (see DEPLOY.md)" >&2; exit 1; fi
	@echo "largest file: $$(find $(OUT) -type f -printf '%s\t%p\n' | sort -rn | head -1 | cut -f1) bytes / $(MAX_FILE_BYTES)"

preview: site ## serve the built site locally with wrangler (no account needed)
	$(WRANGLER) pages dev $(OUT)

deploy: preflight ## upload the built site to the Cloudflare Pages project
	$(WRANGLER) pages deploy $(OUT) \
	  --project-name $(PROJECT) \
	  --branch $(BRANCH) \
	  $(if $(COMMIT),--commit-hash $(COMMIT) --commit-dirty=true,)

project: ## create the Pages project (once per account)
	$(WRANGLER) pages project create $(PROJECT) \
	  --production-branch $(PRODUCTION_BRANCH)

whoami: ## show which Cloudflare account the credentials resolve to
	$(WRANGLER) whoami

check: ## show the toolchain versions this Makefile will use
	@echo "python:   $(PYTHON) -- $$($(PYTHON) --version 2>&1)"
	@echo "node:     $$(node --version 2>/dev/null || echo missing)"
	@echo "wrangler: $$($(WRANGLER) --version 2>/dev/null || echo unavailable)"

clean: ## remove the built site
	rm -rf $(OUT)

clean-db: ## remove the unpacked database and the build stamp
	rm -rf $(BUILD)

distclean: clean clean-db ## remove everything this Makefile generates
