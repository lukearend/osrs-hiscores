export SHELL:=/bin/bash
.DEFAULT_GOAL := help

all: init scrape cluster analytics app  ## Scrape data, process it and build final application data.
build: init download test analytics app ## Build application data from downloaded, pre-scraped data.
run: mongo-start                        ## Run main application.
	source env/bin/activate && python3 app

# Setup -------------------------------------------------------------------------------------------

include ref/makepaths
ifneq (,$(wildcard ./.env))
    include .env
    export
endif
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
stats_file=$(ROOT_DIR)/$(STATS_FILE)
centroids_file=$(ROOT_DIR)/$(CENTROIDS_FILE)
clusterids_file=$(ROOT_DIR)/$(CLUSTERIDS_FILE)
clust_xyz_file=$(ROOT_DIR)/$(CLUST_XYZ_FILE)
clust_quartiles_file=$(ROOT_DIR)/$(CLUST_QUARTILES_FILE)
appdata_file=$(ROOT_DIR)/$(APPDATA_FILE)

init: env mongo-pull

env:
	echo "building virtual environment..."
	python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info

mongo-pull:
	docker pull mongo

# Data scraping -----------------------------------------------------------------------------------

scrape: mongo-start scrape-hiscores export-scraped-stats ## Scrape stats for the top 2 million OSRS accounts.

scrape-hiscores:
	source env/bin/activate && cd src/scrape && \
	python -m scrape_hiscores --mongo-url $(OSRS_MONGO_URI) --mongo-coll $(SCRAPE_COLLECTION) \
	--start-rank 1 --stop-rank 2000000 --num-workers 28

export-scraped-stats:
	source env/bin/activate && cd src/scrape && \
	python -m export_collection $< $(stats_file).csv

$(stats_file).csv: export-scraped-stats
$(stats_file).pkl: stats-csv-to-pkl

# Player clustering -------------------------------------------------------------------------------

cluster: fit-clusters cluster-players ## Cluster players according to scraped stats.

fit-clusters: $(stats_file).pkl
	source env/bin/activate && cd src/cluster && \
	python -m fit_clusters $< $(centroids_file).pkl

cluster-players: $(stats_file).pkl $(centroids_file).pkl
	source env/bin/activate && cd src/cluster && \
	python -m cluster_players $^ $(clusterids_file).pkl --num-clusters $(KMEANS_K)

$(centroids_file).pkl: fit-clusters
$(clusterids_file).pkl: cluster-players
$(centroids_file).csv: centroids-pkl-to-csv
$(clusterids_file).csv: clusterids-pkl-to-csv

# Cluster analytics -------------------------------------------------------------------------------

analytics: dim-reduce-clusters compute-quartiles ## Reduce cluster dimensionality and compute quartiles.

dim-reduce-clusters:
	source env/bin/activate && cd src/models && \
	python -m dim_reduce_clusters $(centroids_file) $(clust_xyz_file) \
		--num-neighbors $(UMAP_NUM_NEIGHBORS) --min-dist $(UMAP_MIN_DIST)

compute-quartiles:
	source env/bin/activate && cd src/results && \
	python -m compute_quartiles $(stats_file) $(clusterids_file) $(clust_quartiles_file)

$(clust_xyz_file): dim-reduce-clusters
$(clust_quartiles_file): compute-quartiles

# Application -------------------------------------------------------------------------------------

app: build-app-data mongo-start build-database ## Build data file and database for application to use.

build-app-data: $(centroids_file) $(clust_xyz_file) $(clust_quartiles_file)
	source env/bin/activate && cd src/results && \
	python -m build_app_data $^ $(app_data_file)

build-database:
	source env/bin/activate && cd src/app && \
	if ! python check_collection $(clusterids_file) $(APPDATA_COLLECTION) ; then \
  		python -m build_database $(stats_file) $(clusterids_file) \
  		--url $(OSRS_MONGO_URI) --collection $(APPDATA_COLLECTION)

mongo-start:
	cd bin && ./start_mongo

# Data upload/download ----------------------------------------------------------------------------

download: ## Download finalized dataset (player stats and clusters).
	source env/bin/activate && \
	bin/download_dataset $(stats_file).pkl $(centroids_file).pkl $(clusterids_file).pkl

upload-s3:
	aws s3 cp $(app_data_file).pkl s3://$(OSRS_APPDATA_BUCKET)/app-data.pkl && \
	aws s3 cp $(centroids_file).pkl s3://$(OSRS_DATASET_BUCKET)/cluster-centroids.pkl && \
	aws s3 cp $(clusterids_file).pkl s3://$(OSRS_DATASET_BUCKET)/player-clusters.pkl && \
	aws s3 cp $(stats_file).pkl s3://$(OSRS_DATASET_BUCKET)/player-stats.pkl

upload-gdrive: csv-files
	upload_gdrive $(stats_file).csv $(centroids_file).csv $(clusterids_file).csv

csv-files: $(stats_file).csv $(centroids_file).csv $(clusterids_file).csv

$(stats_file).csv: stats-pkl-to-csv
$(centroids_file).csv: centroids-pkl-to-csv
$(clusterids_file).csv: clusterids-pkl-to-csv

%-pkl-to-csv:
	source env/bin/activate && cd src/data && \
	python -m $*_pkl_to_csv $($*_file).pkl $($*_file).csv

# Testing -----------------------------------------------------------------------------------------

test_data_file:=$(ROOT_DIR)/test/data/player-stats-small.csv

test: lint test-units test-pipeline ## Run unit and integration tests.

lint:
	source env/bin/activate && \
	pycodestyle app src --ignore=E501,E302 && \
	echo "code check passed"

test-units: $(test_data_file)
	source env/bin/activate && cd test && \
	OSRS_SPLITS_FILE=$(ROOT_DIR)/test/data_splits.json pytest test -sv

test-pipeline:
	cd test && ./test_pipeline $(test_data_file)

$(test_data_file):
	source env/bin/activate && cd test && \
	python -m build_stats_small $(stats_file) $@

# Other -------------------------------------------------------------------------------------------

clean: env-clean scrape-clean cluster-clean analytics-clean app-clean csv-clean ## Remove all generated artifacts.

env-clean:
	rm -rf env

scrape-clean:
	rm -f $(raw_stats_file).csv
	rm -f $(stats_file).pkl

cluster-clean:
	rm -f $(centroids_file).pkl
	rm -f $(clusterids_file).pkl

analytics-clean:
	rm -f $(clust_xyz_file).pkl
	rm -f $(clust_quartiles_file).pkl

app-clean:
	rm -f $(app_data_file).pkl
	rm -rf volume

csv-clean:
	rm -f $(stats_file).csv
	rm -f $(centroids_file).csv
	rm -f $(clusterids_file).csv

ec2-%: # options: status, start, stop, connect, setup
	cd bin/dev && ./ec2_instance $*

help: ## Show this help.
	grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
