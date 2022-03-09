export SHELL:=/bin/bash
.DEFAULT_GOAL := help

all: init scrape cluster analytics app  ## Scrape data, process it and build final application data.
build: init download test analytics app ## Build application data from downloaded, pre-scraped data.
run:                                    ## Run main application.
	source env/bin/activate && python3 app

# Setup -------------------------------------------------------------------------------------------

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
DATA_DIR:="$(DATA_DIR)/data"
raw_stats_file="$(DATA_DIR)/raw/stats-raw.csv"
stats_file="$(DATA_DIR)/processed/player-stats.csv"
centroids_file="$(DATA_DIR)/processed/cluster-centroids.pkl"
clusterids_file="$(DATA_DIR)/processed/player-clusters.pkl"
clust_xyz_file="$(DATA_DIR)/interim/clusters-xyz.pkl"
clust_quartiles_file="$(DATA_DIR)/interim/cluster-quartiles.pkl"
appdata_file="$(DATA_DIR)/processed/app-data.pkl"
mongo_collection="$(ROOT_DIR)/players"

init: env pull-mongo

env:
	echo "building virtual environment..."
	python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info

pull-mongo:
	docker pull mongo

# Data scraping -----------------------------------------------------------------------------------

scrape: scrape-stats cleanup-stats ## Scrape stats for the top 2 million OSRS accounts.

scrape-stats:
	source env/bin/activate && cd src/scrape && \
	if ! python -m check_complete ; then \
		python -m scrape_stats $(raw_stats_file) --start 1 --end 80000 --random


cleanup-stats: $(raw_stats_file)
	source env/bin/activate && cd src/cluster && \
	python -m cleanup_stats $< $(stats_file)

$(raw_stats_file): scrape-stats
$(stats_file): cleanup-stats
.PHONY: $(raw_stats_file)

# Player clustering -------------------------------------------------------------------------------

cluster: fit-clusters cluster-players ## Cluster players according to scraped stats.

fit-clusters: $(stats_file)
	source env/bin/activate && cd src/cluster && \
	python -m fit_clusters $< $(centroids_file)

cluster-players: $(stats_file) $(centroids_file)
	source env/bin/activate && cd src/cluster && \
	python -m cluster_players $^ $(clusterids_file) --num-clusters $(KMEANS_K)

$(centroids_file): fit-clusters
$(clusterids_file): cluster-players

# Cluster analytics -------------------------------------------------------------------------------

analytics: dim-reduce-clusters compute-quartiles ## Reduce dimensionality of centroids and compute quartiles.

dim-reduce-clusters:
	source env/bin/activate && cd src/models \
	python -m dim_reduce_clusters $(centroids_file) $(clust_xyz_file) \
		--num-neighbors $(UMAP_NUM_NEIGHBORS) --min-dist $(UMAP_MIN_DIST)

compute-quartiles:
	source env/bin/activate && cd src/results \
	python -m compute_quartiles $(stats_file) $(clusterids_file) $(clust_quartiles_file)

$(clust_xyz_file): dim-reduce-clusters
$(clust_quartiles_file): compute-quartiles

# Application -------------------------------------------------------------------------------------

app: build-app-data start-mongo build-database ## Build data file and database for application to use.

build-app-data: $(centroids_file) $(clust_xyz_file) $(clust_quartiles_file)
	source env/bin/activate && cd src/results && \
	python build_app_data.py $^ $(app_data_file)

build-database:
	source env/bin/activate && cd src/app && \
	if ! python check_collection $(clusterids_file) $(MONGO_COLLECTION) ; then \
  		python build_database $(stats_file) $(clusterids_file) --collection $(MONGO_COLLECTION)

start-mongo:
	cd bin && ./start_mongo

# Data upload/download ----------------------------------------------------------------------------

centroids_file_csv:=$(subst .pkl,.csv,$(centroids_file))
clusters_file_csv:=$(subst .pkl,.csv,$(clusters_file))

download: ## Download finalized dataset of stats and clustering results.
	source env/bin/activate && cd bin && ./download_dataset

upload-artifacts: upload-app-data upload-stats-data upload-cluster-data

upload-app-data:
	aws s3 cp $(app_data_file) s3://$(OSRS_S3_BUCKET)/app-data.pkl

upload-stats-data:
	aws s3 cp $(stats_file) s3://$(OSRS_S3_BUCKET)/player-stats.csv

upload-cluster-data:
	aws s3 cp $(centroids_file_csv) s3://$(OSRS_S3_BUCKET)/cluster-centroids.csv && \
	aws s3 cp $(clusters_file_csv) s3://$(OSRS_S3_BUCKET)/player-clusters.csv

convert-pkl-to-csv:
	source env/bin/activate && cd src/data && \
	python -m centroids_pkl_to_csv $(centroids_file) $(centroids_file_csv) && \
	python -m clusters_pkl_to_csv $(clusters_file) $(clusters_file_csv)

convert-csv-to-pkl:
	source env/bin/activate && cd src/data && \
	python -m centroids_csv_to_pkl $(centroids_file_csv) $(centroids_file) && \
	python -m clusters_csv_to_pkl $(clusters_file_csv) $(clusters_file)

# Testing -----------------------------------------------------------------------------------------

test_data_file:=$(ROOT_DIR)/test/data/player-stats-small.csv

test: lint test-units test-pipeline ## Run unit and integration tests.

lint:
	source env/bin/activate && \
	pycodestyle app src --ignore=E501,E302 && \
	echo "code check passed"

test-units: $(test_data_file)
	@source env/bin/activate && cd test && \
	OSRS_SPLITS_FILE=$(ROOT_DIR)/test/data_splits.json pytest test -sv

test-pipeline:
	@cd test && ./test_pipeline $(test_data_file)

$(test_data_file):
	source env/bin/activate && cd test && \
	python build_stats_small.py $(stats_file) $@

# Other -------------------------------------------------------------------------------------------

clean: env-clean scrape-clean cluster-clean analytics-clean app-clean ## Remove all generated artifacts.

env-clean:
	rm -rf env

scrape-clean:
	rm -f $(raw_stats_file)
	rm -f $(stats_file)

cluster-clean:
	rm -f $(centroids_file)
	rm -f $(clusterids_file)

analytics-clean:
	rm -f $(clust_xyz_file)
	rm -f $(clust_quartiles_file)

app-clean:
	rm -f $(app_data_file)
	rm -rf volume

ec2-%: # options: status, start, stop, connect, setup
	@cd bin/dev && ./ec2_instance $*

help: ## Show this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
