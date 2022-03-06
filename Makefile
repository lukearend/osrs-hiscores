export SHELL:=/bin/bash
ifneq (,$(wildcard ./.env))
	include .env
	export
endif
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
DATA_DIR:=$(ROOT_DIR)/data

stats_file:="$(DATA_DIR)/processed/player-stats.csv"
centroids_file:="$(DATA_DIR)/processed/cluster-centroids.csv"
clusterids_file:="$(DATA_DIR)/processed/player-clusters.csv"
clust_xyz_file:="$(DATA_DIR)/interim/clusters_xyz.pkl"
clust_analytics_file:="$(DATA_DIR)/interim/cluster_analytics.pkl"

kmeans_params:="$(ROOT_DIR)/ref/kmeans_params.json"
umap_params:="$(ROOT_DIR)/ref/umap_params.json"

appdata_file:="$(DATA_DIR)/processed/app_data.pkl"
player_coll:="players"

# Top-level ---------------------------------------------------------------------------------------
.DEFAULT_GOAL := help
all: init scrape cluster analytics app  ## Scrape data, process it and build final application data.
build: init download test analytics app ## Build application data from downloaded, already-scraped data.
run: mongo-pull mongo-start app-run     ## Run main application.
clean: env-clean scrape-clean cluster-clean analytics-clean app-clean ## Remove all generated artifacts.
.PHONY: all build run clean

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

.PHONY: init env env-clean

# Data scraping -----------------------------------------------------------------------------------
scrape: $(stats_file) ## Run data scrape of OSRS hiscores.

raw_usernames_file:="$(DATA_DIR)/raw/usernames-raw.csv"
usernames_file:="$(DATA_DIR)/interim/usernames.csv"
raw_stats_file:="$(DATA_DIR)/raw/stats-raw.csv"

scrape-clean: # Keep raw dump files.
	rm -f $(usernames_file)
	rm -f $(stats_file)

scrape-clobber: # Delete all files from scraping process.
	rm -f $(raw_usernames_file)
	rm -f $(usernames_file)
	rm -f $(raw_stats_file)
	rm -f $(stats_file)

.PHONY: scrape scrape-clean scrape-clobber

$(raw_usernames_file):
	bin/scrape_usernames $@

$(usernames_file): $(raw_usernames_file)
	@source env/bin/activate && python src/scrape/cleanup_usernames.py $< $@

$(raw_stats_file): $(usernames_file)
	bin/scrape_stats $< $@

$(stats_file): $(raw_stats_file)
	@source env/bin/activate && python src/scrape/cleanup_stats.py $< $@

.PRECIOUS: $(raw_usernames_file) $(raw_stats_file)

# Player clustering -------------------------------------------------------------------------------
cluster: $(centroids_file) $(clusterids_file) ## Cluster players according to scraped stats.

cluster-clean:
	rm -f $(centroids_file)
	rm -f $(clusterids_file)

.PHONY: cluster cluster-clean

$(centroids_file):
	@source env/bin/activate && python src/models/fit_clusters.py $(stats_file) $@ \
	--params $(kmeans_params) --verbose

$(clusterids_file): $(centroids_file)
	@source env/bin/activate && python sr/models/cluster_players.py $(stats_file) $< $@

# Cluster analytics -------------------------------------------------------------------------------
analytics: $(clust_xyz_file) $(clust_analytics_file) ## Reduce dimensionality and analyze clusters.

analytics-clean:
	rm -f $(cluster_xyz_file)

.PHONY: analytics analytics-clean

$(clust_xyz_file):
	@source env/bin/activate && \
	python src/models/dim_reduce_clusters.py $(centroids_file) $@ --params $(umap_params)

$(clust_analytics_file):
	@source env/bin/activate && \
	python src/results/postprocess_clusters.py $(stats_file) $(clusterids_file) $@

# Application -------------------------------------------------------------------------------------
app: $(appdata_file) build-db ## Build data file and database for application to use.

app-run:
	@source env/bin/activate && python app

app-clean:
	rm -rf volume
	rm -f $(appdata_file)

build-db:
	@source env/bin/activate && \
	bin/build_database $(stats_file) $(clusterids_file) $(player_coll) $(OSRS_MONGO_URI)

.PHONY: app app-run app-clean build-db

$(appdata_file): $(centroids_file) $(clust_analytics_file) $(clust_xyz_file)
	@source env/bin/activate && python src/results/build_app_data.py $^ $@

# Testing -----------------------------------------------------------------------------------------
test_data_file:=$(ROOT_DIR)/test/data/player-stats-tiny.csv

test: $(test_data_file) lint test-units test-pipeline ## Run tests for data processing pipeline.

test-units: $(test_data_file)
	@source env/bin/activate && pytest test -sv

test-pipeline:
	@cd test && ./test_pipeline

.PHONY: test lint test-units test-pipeline

$(test_data_file):
	@source env/bin/activate && python test/build_stats_small.py $(stats_file) $@

# Other -------------------------------------------------------------------------------------------
upload-appdata:
	@cd bin && ./upload_appdata

upload-dataset:
	@cd bin && ./upload_dataset

download: ## Download finalized dataset (player stats and clusters).
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

lint: ## Run code style checker.
	@source env/bin/activate && pycodestyle app src --ignore=E501,E302 && \
	echo "code check passed"

help: ## Show this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: vim-binding nbextensions notebook help
