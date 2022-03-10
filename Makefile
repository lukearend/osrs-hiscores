export SHELL:=/bin/bash
.DEFAULT_GOAL := help

all: init scrape cluster analytics app  ## Scrape data, process it and build final application data.
build: init download test analytics app ## Build application data from downloaded, pre-scraped data.
run: start-mongo                        ## Run main application.
	source env/bin/activate && python3 app

# Setup -------------------------------------------------------------------------------------------

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
DATA_DIR:="$(ROOT_DIR)/data"
raw_stats_file="$(DATA_DIR)/raw/stats-raw"
stats_file="$(DATA_DIR)/processed/player-stats"
centroids_file="$(DATA_DIR)/processed/cluster-centroids"
clusterids_file="$(DATA_DIR)/processed/player-clusters"
clust_xyz_file="$(DATA_DIR)/interim/clusters-xyz"
clust_quartiles_file="$(DATA_DIR)/interim/cluster-quartiles"
appdata_file="$(DATA_DIR)/processed/app-data"
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

scrape: scrape-stats cleanup-stats stats-csv-to-pkl ## Scrape stats for the top 2 million OSRS accounts.

scrape-stats:
	source env/bin/activate && cd src/scrape && \
	if ! python -m check_complete ; then \
		python -m scrape_stats $(raw_stats_file).csv --start 1 --end 80000 --random

cleanup-stats: $(raw_stats_file).csv
	source env/bin/activate && cd src/scrape && \
	python -m cleanup_stats $< $(stats_file).pkl

$(raw_stats_file).csv: scrape-stats
$(stats_file).pkl: cleanup-stats
$(stats_file).csv: stats-pkl-to-csv
.PHONY: $(raw_stats_file).csv

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

app: build-app-data start-mongo build-database ## Build data file and database for application to use.

build-app-data: $(centroids_file) $(clust_xyz_file) $(clust_quartiles_file)
	source env/bin/activate && cd src/results && \
	python -m build_app_data $^ $(app_data_file)

build-database:
	source env/bin/activate && cd src/app && \
	if ! python check_collection $(clusterids_file) $(MONGO_COLLECTION) ; then \
  		python -m build_database $(stats_file) $(clusterids_file) --collection $(MONGO_COLLECTION)

start-mongo:
	cd bin && ./start_mongo

# Data upload/download ----------------------------------------------------------------------------

download: download-stats download-clusters ## Download finalized dataset (player stats and clusters).
	source env/bin/activate && \
	bin/download_dataset $(stats_file) $(centroids_file) $(clusterids_file) && \
	src/data/python -m pkls_to_csv $(centroids_file) $(clusterids_file)

csv-files: $(stats_file).csv $(centroids_file).csv $(clusterids_file).csv

$(stats_file).csv: stats-pkl-to-csv
$(centroids_file).csv: centroids-pkl-to-csv
$(clusterids_file).csv: clusterids-pkl-to-csv

%-pkl-to-csv:
	source env/bin/activate && cd src/data && \
	python -m $*_pkl_to_csv $($*_file).pkl $($*_file).csv

upload-gdrive: csv-files
	upload_gdrive $(stats_file).csv $(centroids_file).csv $(clusterids_file).csv

upload-app-data:
	aws s3 cp $(app_data_file) s3://$(OSRS_APPDATA_BUCKET)/app-data.pkl && \

upload-s3:
	aws s3 cp $(stats_file) s3://$(OSRS_DATASET_BUCKET)/player-stats.csv && \
	aws s3 cp $(centroids_file) s3://$(OSRS_DATASET_BUCKET)/cluster-centroids.pkl && \
	aws s3 cp $(clusterids_file) s3://$(OSRS_DATASET_BUCKET)/player-clusters.pkl && \



centroids_file_csv:=$(subst .pkl,.csv,$(centroids_file))
clusterids_file_csv:=$(subst .pkl,.csv,$(clusterids_file))

$(centroids_file_csv):  write-centroids-csv
	source env/bin/activate && cd src/data && \
	python -m centroids_pkl_to_csv $(centroids_file)

$(clusterids_file_csv): write-clusterids-csv
	source env/bin/activate && cd src/data && \
	python -m clusters_pkl_to_csv $(centroids_file)

upload-gdrive: $(centroids_file_csv) $(clusterids_File_csv)




upload-artifacts: upload-app upload-stats upload-clusters
	upload_artifacts $(app_data_file)

download-stats:
	aws s3 cp s3://$(OSRS_S3_BUCKET)/player-stats.csv $(stats_file)

download-clusters:
	aws s3 cp s3://$(OSRS_S3_BUCKET)/cluster-centroids.csv $(centroids_file_csv)
	aws s3 cp s3://$(OSRS_S3_BUCKET)/player-clusters.csv $(clusterids_file_csv)

upload-app:

upload-stats:
	aws s3 cp $(app_data_file) s3://$(OSRS_S3_BUCKET)/app-data.pkl
	aws s3 cp $(stats_file) s3://$(OSRS_S3_BUCKET)/player-stats.csv
	aws s3 cp $(centroids_file_csv) s3://$(OSRS_S3_BUCKET)/cluster-centroids.csv && \
	aws s3 cp $(clusterids_file_csv) s3://$(OSRS_S3_BUCKET)/player-clusters.csv

upload-clusters:

upload-gdrive:
	cd bin && upload_gdrive $(stats_file).csv $(centroids_file).csv $(clusterids_file).csv

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
	cd bin/dev && ./ec2_instance $*

help: ## Show this help.
	grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
