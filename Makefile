# Road Safety Action Explorer
#   make ingest     fetch + checksum-verify raw public files, stage them (data/raw, data/staging; git-ignored)
#   make transform  dbt build on raw records -> export committed aggregates + marts + data dictionary
#   make test       ruff + pytest + dbt build on the committed aggregates + rebuild-equality check
#   make site       static GitHub Pages site -> site/_build/
#   make app        Streamlit app (runs offline from committed data/marts)

PYTHON ?= python
DBT ?= dbt
DBT_ARGS = --profiles-dir . --no-use-colors

.PHONY: help setup ingest seeds transform test lint pytest dbt-test site app verify-citations refresh-sources check-new-fars clean

help:
	@grep -E '^#  ' Makefile | sed 's/^#  //'

setup:
	$(PYTHON) -m pip install -r requirements.txt

ingest:
	$(PYTHON) -m pipeline.ingest

seeds:
	$(PYTHON) -m pipeline.yaml_to_seeds

transform: seeds
	mkdir -p data/warehouse
	cd dbt && $(DBT) build $(DBT_ARGS) --vars '{source_mode: raw}'
	$(PYTHON) -m pipeline.export --aggregates --marts
	$(PYTHON) -m pipeline.data_dictionary

lint:
	ruff check .
	ruff format --check .

pytest:
	$(PYTHON) -m pytest

# Build every model and run every dbt test from the committed aggregates only (no raw data needed),
# in a separate database, then require the rebuilt marts to match the committed ones byte-for-byte.
dbt-test: seeds
	mkdir -p data/warehouse
	rm -f data/warehouse/ci.duckdb
	cd dbt && RSAE_DUCKDB_PATH=../data/warehouse/ci.duckdb $(DBT) build $(DBT_ARGS)
	$(PYTHON) -m pipeline.export --marts --check --db data/warehouse/ci.duckdb

test: lint dbt-test pytest

site:
	$(PYTHON) -m sitegen.build

app:
	streamlit run app/streamlit_app.py

verify-citations:
	$(PYTHON) -m pipeline.verify_citations

refresh-sources:
	$(PYTHON) -m pipeline.sources refresh

check-new-fars:
	$(PYTHON) -m pipeline.check_new_fars

clean:
	rm -rf data/staging data/warehouse dbt/target dbt/logs site/_build dbt/seeds/generated
