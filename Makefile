ROOT := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
-include .env
export

.DEFAULT_GOAL = help

app: init download-dataset postprocess build-app run-app
all: init test scrape cluster postprocess build-app run-app
finalize: scrape cluster export-csv publish-dataset push-app-data deploy-prod

## ---- Setup and test ----

init: ## Setup repository and install dependencies.
	mkdir -p data/raw data/interim data/final
	python3 -m venv env
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt
	rm -rf *.egg-info
	docker pull mongo

lint: ## Run code check.
	@source env/bin/activate && pycodestyle src scripts --ignore=E301,E302,E402,E501
	@echo "code check passed"

test: lint ## Run self test.
	@source env/bin/activate && pytest test

clean: ## Reset repository to initial state.
	rm -rf data/raw/* data/interim/* data/final/*
	rm -rf env

## ---- Top-level targets ----

scrape: scrape-hiscores clean-scraped-data ## Scrape player stats from the OSRS hiscores.

cluster: cluster-players ## Cluster players according to account similarity.

postprocess: compute-quartiles dim-reduce-clusters ## Analyze clusters and project to lower dimensionality.

build-app: build-app-data populate-app-db ## Build data file and database for application to use.

run-app: ## Run main application locally.
	@source env/bin/activate && bin/start_mongo && python runapp.py

## ---- Finalization ----

push-app-data: ## Upload application data to production.
	cmd/push_app_data

deploy-dev: ## Deploy app to development staging area.
	git push staging development:master

deploy-prod: ## Deploy app to production.
	git push heroku master:master

export-csv: ## Export dataset files from .pkl to CSV format.
	cmd/export_dataset_csv

publish-dataset: ## Publish dataset CSV files to Google Drive.
	cmd/publish_dataset

## ---- Data processing ----

scrape-hiscores: $(SCRAPE_OUT_FILE)
clean-scraped-data: $(PLAYER_STATS_FILE)
cluster-players: $(CLUSTER_IDS_FILE) $(CLUSTER_CENTROIDS_FILE)
compute-quartiles: $(CLUSTER_QUARTILES_FILE)
dim-reduce-clusters: $(CLUSTER_XYZ_FILE)

.SECONDARY: $(SCRAPE_OUT_FILE) # Don't run scraping if player stats already exists.

$(SCRAPE_OUT_FILE):
	cmd/scrape_hiscores $@.tmp && mv $@.tmp $@

$(PLAYER_STATS_FILE):
	@source env/bin/activate && scripts/clean_raw_data.py \
	--in-file $(SCRAPE_OUT_FILE) --out-file $@


$(CLUSTER_IDS_FILE) $(CLUSTER_CENTROIDS_FILE):
	@source env/bin/activate && scripts/cluster_players.py \
	--in-file $(PLAYER_STATS_FILE) --splits-file $(SPLITS_FILE) --params-file $(PARAMS_FILE) \
	--out-clusterids $(CLUSTER_IDS_FILE) --out-centroids $(CLUSTER_CENTROIDS_FILE) --verbose

$(CLUSTER_QUARTILES_FILE):
	@source env/bin/activate && scripts/compute_quartiles.py \
	--splits-file $(SPLITS_FILE) --stats-file $(PLAYER_STATS_FILE) \
	--clusterids-file $(CLUSTER_IDS_FILE) --out-file $@

$(CLUSTER_XYZ_FILE):
	@source env/bin/activate && scripts/dim_reduce_clusters.py \
	--params-file $(PARAMS_FILE) --in-file $(CLUSTER_CENTROIDS_FILE) --out-file $@

$(APP_DATA_FILE):
	@source env/bin/activate && scripts/build_app_data.py \
	--splits-file $(SPLITS_FILE) --clusterids-file $(CLUSTER_IDS_FILE) \
	--centroids-file $(CLUSTER_CENTROIDS_FILE) --quartiles-file $(CLUSTER_QUARTILES_FILE) \
	--xyz-file $(CLUSTER_XYZ_FILE) --out-file $(APP_DATA_FILE)

populate-app-db:
	@source env/bin/activate && bin/start_mongo && scripts/build_app_db.py \
	--stats-file $(PLAYER_STATS_FILE) --clusterids-file $(CLUSTER_IDS_FILE) \
	--mongo-url $(OSRS_MONGO_URI) --collection $(OSRS_MONGO_COLL)

## ---- Other ----

download-dataset:
	@source env/bin/activate && cmd/download_dataset

build-test-data:
	@source env/bin/activate && bin/build_test_data \
	--base-file $(PLAYER_STATS_FILE) --out-file test/data/test-data.csv

ec2-%: # status, start, stop, connect, setup
	@bin/ec2_instance $*

help: ## Print this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: env test
