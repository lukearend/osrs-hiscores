export SHELL:=/bin/bash
export AMBER_LICENSE_ID:=luke-dev

ifneq (,$(wildcard ./.env))
	include .env
	export
endif

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
DATA_RAW:=$(ROOT_DIR)/data/raw
DATA_TMP:=$(ROOT_DIR)/data/interim
DATA_FINAL:=$(ROOT_DIR)/data/processed
TEST_DIR:=$(ROOT_DIR)/test
REF_DIR:=$(ROOT_DIR)/ref

.DEFAULT_GOAL := help

# Top-level ---------------------------------------------------------------------------------------

all: init scrape cluster dimreduce app # Scrape data, process it and build final application data.

build: init download test dimreduce app # Build application data from downloaded, already-scraped data.

run: # Run Dash application.
	@source env/bin/activate && python app

clean: env-clean scrape-clean cluster-clean dimreduce-clean app-clean ## Remove all generated artifacts.

.PHONY: all everything run clean

# Setup -------------------------------------------------------------------------------------------
init: env mongo-pull mongo-start ## Setup project dependencies.

env:
	@echo "building virtual environment..."
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info

env-clean:
	rm -rf env

.PHONY: init env env-clean clean

# Data scraping -----------------------------------------------------------------------------------
scrape: $(DATA_FINAL)/player-stats.csv ## Run data scrape of OSRS hiscores.

$(DATA_RAW)/usernames-raw.csv:
	cd bin && ./scrape_usernames $@

$(DATA_TMP)/usernames.csv: $(DATA_RAW)/usernames-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python cleanup_usernames.py $< $@

$(DATA_RAW)/stats-raw.csv: $(DATA_TMP)/usernames.csv
	cd bin && ./scrape_stats $< $@

$(DATA_FINAL)/player-stats.csv: $(DATA_RAW)/stats-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python cleanup_stats.py $(DATA_RAW)/stats-raw.csv $@

scrape-clean: # Keep raw dump files.
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_FINAL)/player-stats.csv

scrape-clobber: # Delete all files from scraping process.
	rm -f $(DATA_RAW)/usernames-raw.csv
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_RAW)/stats-raw.csv
	rm -f $(DATA_FINAL)/player-stats.csv

.PHONY: scrape scrape-clean scrape-clobber
.PRECIOUS: $(DATA_RAW)/usernames-raw.csv $(DATA_RAW)/stats-raw.csv

# Clustering --------------------------------------------------------------------------------------
cluster: $(DATA_FINAL)/player-clusters.csv ## Cluster players according to scraped stats.

$(DATA_FINAL)/cluster-centroids.csv:
	@source env/bin/activate && cd src/models && \
	python fit_clusters.py $(DATA_FINAL)/player-stats.csv $@ -p $(REF_DIR)/kmeans_params.json --verbose

$(DATA_FINAL)/player-clusters.csv: $(DATA_FINAL)/cluster-centroids.csv
	@source env/bin/activate && cd src/models && \
	python cluster_players.py $(DATA_FINAL)/player-stats.csv $< $@

cluster-clean:
	rm -f $(DATA_FINAL)/cluster-centroids.csv
	rm -f $(DATA_FINAL)/player-clusters.csv

.PHONY: cluster cluster-clean

# Cluster analytics -------------------------------------------------------------------------------
dimreduce: $(DATA_TMP)/clusters_xyz.pkl ## Reduce cluster dimensionality for visualization.

$(DATA_TMP)/clusters_xyz.pkl:
	@source env/bin/activate && cd src/models && \
	python dim_reduce_clusters.py $(DATA_FINAL)/cluster-centroids.csv $@ -p $(REF_DIR)/umap_params.json

$(DATA_TMP)/cluster_analytics.pkl:
	@source env/bin/activate && cd src/results && \
	python postprocess_clusters.py $(DATA_FINAL)/player-stats.csv $(DATA_FINAL)/player-clusters.csv $@

dimreduce-clean:
	rm -f $(DATA_TMP)/clusters_xyz.pkl

.PHONY: dimreduce dimreduce-clean

# Application -------------------------------------------------------------------------------------
app: $(DATA_FINAL)/app_data.pkl build-db ## Build data file and database for visualization app.

$(DATA_FINAL)/app_data.pkl: $(DATA_FINAL)/cluster-centroids.csv $(DATA_TMP)/cluster_analytics.pkl $(DATA_TMP)/clusters_xyz.pkl
	@source env/bin/activate && cd src/results && python build_app_data.py $^ $@

build-db:
	@source env/bin/activate && cd bin && \
	./build_database $(DATA_FINAL)/player-stats.csv $(DATA_FINAL)/player-clusters.csv players -u $(OSRS_MONGO_URI)

app-clean:
	rm -rf volume
	rm -f $(DATA_FINAL)/app_data.pkl

.PHONY: app build-db app-clean

# Testing -----------------------------------------------------------------------------------------

test: lint test-units test-pipeline ## Run tests for processing pipeline.

$(TEST_DIR)/data/player-stats-1000.csv:
	@source env/bin/activate && cd test && \
	python build_stats_small.py $(DATA_FINAL)/player-stats.csv $@

lint: ## Run code style checker.
	@source env/bin/activate && \
	pycodestyle app src --ignore=E501,E302 && \
	echo "code check passed"

test-units: $(TEST_DIR)/data/player-stats-1000.csv
	@source env/bin/activate && pytest test -sv

test-pipeline: $(TEST_DIR)/data/player-stats-1000.csv
	@cd test && ./test_pipeline


.PHONY: test lint test-units test-pipeline

# Other -------------------------------------------------------------------------------------------

upload-appdata:
	@cd bin && ./upload_appdata

upload-dataset:
	@cd bin && ./upload_dataset

download: ## Download processed dataset from S3.
	@source env/bin/activate && \
	cd bin && ./download_dataset

ec2-%: ## EC2 instance: status, start, stop, connect, setup, dockerd
	@cd bin && ./ec2_instance $*

mongo-%: ## Mongo instance container: pull, status, start, stop
	@cd bin && ./mongo_instance $*

.PHONY: upload-appdata upload-dataset download ec2-% mongo-%

vim-binding:
	@source env/bin/activate && \
	jupyter contrib nbextensions install && \
	cd $(shell jupyter --data-dir)/nbextensions && \
	git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding || \
	cd vim_binding && git pull

nbextensions: vim-binding
	jupyter nbextension enable vim_binding/vim_binding
	jupyter nbextension enable rubberband/main
	jupyter nbextension enable toggle_all_line_numbers/main
	jupyter nbextension enable varInspector/main

notebook: nbextensions ## Start a local jupyter notebook server.
	@source env/bin/activate && jupyter notebook

help: ## Show this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: vim-binding nbextensions notebook help
