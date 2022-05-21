export SHELL := /bin/bash
ROOT := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

.DEFAULT_GOAL = help

## ---- End-to-end ----

build:    setup download app run                ## Build and run final application from downloaded data.
all:      setup scrape cluster analysis app run ## Build and run final application from scratch.

## ---- Top-level ----

setup:    init-repo build-env pull-mongo       ## Setup repository and install dependencies.
scrape:   scrape-hiscores clean-scraped-data   ## Scrape top 2 million players from the OSRS hiscores.
cluster:  cluster-hiscores-data                ## Cluster players according to account similarity.
analysis: compute-quartiles dimreduce-clusters ## Analyze and postprocess clustering results.
app:      app-blob app-db                      ## Build data blob and database needed by main application.
run:      start-mongo run-app                  ## Run main application.
test:     lint test-scrape test-scripts        ## Run test suite.

export:   export-dataset                       ## Export finalized dataset to CSV files.
publish:  upload-dataset build-app-prod        ## Upload finalized dataset and production app data.
download: download-prebuilt-data               ## Download pre-scraped data with clustering results.

## ---- Setup ----

init-repo:
	mkdir -p data/raw data/interim data/final

build-env:
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt
	rm -rf *.egg-info

pull-mongo:
	docker pull mongo

## ---- Scraping and cleaning ----

player_stats_raw    := $(ROOT)/data/raw/player-stats-raw.csv
player_stats := $(ROOT)/data/interim/player-stats.pkl

scrape-hiscores: $(player_stats_raw)
clean-scraped-data: $(player_stats)

$(player_stats_raw):
	@source env/bin/activate && cd scripts && \
	python scrape_hiscores.py --start-rank 1 --stop-rank 2000000 --num-workers 28 \
	                          --log-file $(ROOT)/data/raw/scrape.log --log-level INFO \
	                          --out-file $(player_stats_raw).tmp --vpn
	mv $(player_stats_raw).tmp $(player_stats_raw)

$(player_stats): $(player_stats_raw)
	@source env/bin/activate && cd scripts && \
	python clean_raw_data.py --in-file $< --out-file $@

.SECONDARY: $(player_stats_raw) # Don't require $(stats_raw) if $(player_stats) already exists.

## ---- Clustering and analysis ----

cluster_ids       := $(ROOT)/data/interim/player-clusterids.pkl
cluster_centroids := $(ROOT)/data/interim/cluster-centroids.pkl
cluster_quartiles := $(ROOT)/data/interim/cluster-quartiles.pkl
cluster_xyz       := $(ROOT)/data/interim/cluster-xyz.pkl

cluster-hiscores-data: $(cluster_ids) $(cluster_centroids)
dimreduce-clusters: $(cluster_xyz)
compute-quartiles: $(cluster_quartiles)

$(cluster_ids) $(cluster_centroids): $(player_stats)
	@source env/bin/activate && cd scripts && \
	python cluster_players.py --in-file $< \
                              --splits-file $(ROOT)/ref/skill-splits.json \
	                          --params-file $(ROOT)/ref/split-params.json \
	                          --out-clusterids $(cluster_ids) \
	                          --out-centroids $(cluster_centroids) \
	                          --verbose

$(cluster_quartiles): $(player_stats) $(cluster_ids)
	@source env/bin/activate && cd scripts && \
	python compute_quartiles.py --splits-file $(ROOT)/ref/skill-splits.json \
	                            --stats-file $(word 1,$^) \
	                            --clusterids-file $(word 2,$^) \
	                            --out-file $@ \

$(cluster_xyz): $(cluster_centroids)
	@source env/bin/activate && cd scripts && \
	python dim_reduce_clusters.py --params-file $(ROOT)/ref/split-params.json \
	                              --in-file $< \
	                              --out-file $@

## ---- Main application ----

app_data   := $(ROOT)/data/interim/app-data.pkl
mongo_url  := $(or $(OSRS_MONGO_URI), 'localhost:27017')
mongo_coll := $(or $(OSRS_MONGO_COLL), 'players')

app-blob: $(app_data)

app-db: start-mongo $(player_stats) $(cluster_ids)
	@source env/bin/activate && cd scripts && \
	python build_app_db.py --stats-file $(word 1,$^) \
	                       --clusterids-file $(word 2,$^) \
	                       --mongo-url $(mongo_url) \
	                       --collection players

$(app_data): $(cluster_ids) $(cluster_centroids) $(cluster_quartiles) $(cluster_xyz)
	@source env/bin/activate && cd scripts && \
	python build_app_data.py --splits-file $(splits) \
	                         --clusterids-file $(word 1,$^) \
	                         --centroids-file $(word 2,$^) \
	                         --quartiles-file $(word 3,$^) \
	                         --xyz-file $(word 4,$^) \
	                         --out-file $@

run-app: start-mongo
	@source env/bin/activate && \
	export OSRS_MONGO_URI=$(mongo_url) && \
	export OSRS_APPDATA_URI=$(app_data) && \
	export OSRS_DISABLE_AUTH=true && \
	python app.py

# ---- Finalization ----

export-dataset: export-player-stats export-cluster-ids export-cluster-centroids
build-app-prod: app-blob app-db upload-app-blob

player_stats_final      := $(ROOT)/data/final/player-stats.csv
cluster_ids_final       := $(ROOT)/data/final/player-clusterids.csv
cluster_centroids_final := $(ROOT)/data/final/cluster-centroids.csv

export-player-stats: $(player_stats_final)
export-cluster-ids: $(cluster_ids_final)
export-cluster-centroids: $(cluster_centroids_final)

$(player_stats_final): $(player_stats)
	@source env/bin/activate && \
	bin/pkl_to_csv --pkl-file $< --csv-file $@ --type players

$(cluster_ids_final): $(cluster_ids)
	@source env/bin/activate && \
	bin/pkl_to_csv --pkl-file $< --csv-file $@ --type clusterids

$(cluster_centroids_final): $(cluster_centroids)
	@source env/bin/activate && \
	bin/pkl_to_csv --pkl-file $< --csv-file $@ --type centroids

upload-app-blob:
	@source env/bin/activate && \
	bin/upload_s3 $(app_data) $(OSRS_APPDATA_URI)

# ---- Upload/download ----

download-dataset: download-player-stats download-cluster-ids download-cluster-centroids
upload-dataset: upload-player-stats upload-cluster-ids upload-cluster-centroids publish-gdrive

player_stats_s3      := "s3://osrshiscores/player-stats.pkl"
cluster_ids_s3       := "s3://osrshiscores/player-clusters.pkl"
cluster_centroids_s3 := "s3://osrshiscores/cluster-centroids.pkl"

download-player-stats:
	@source env/bin/activate && \
	bin/download_s3 $(player_stats_s3) $(player_stats)

download-cluster-ids:
	@source env/bin/activate && \
	bin/download_s3 $(cluster_ids_s3) $(cluster_ids)

download-cluster-centroids:
	@source env/bin/activate && \
	bin/download_s3 $(cluster_centroids_s3) $(cluster_centroids)

upload-player-stats:
	@source env/bin/activate && \
	bin/upload_s3 $(player_stats) $(player_stats_s3)

upload-cluster-ids:
	@source env/bin/activate && \
	bin/upload_s3 $(cluster_ids) $(cluster_ids_s3)

upload-cluster-centroids:
	@source env/bin/activate && \
	bin/upload_s3 $(cluster_centroids) $(cluster_centroids_s3)

publish-gdrive:
	@gdrive upload $(cluster_centroids_final) -p $(OSRS_GDRIVE_FOLDER) --name cluster-centroids.csv
	@gdrive upload $(cluster_ids_final) -p $(OSRS_GDRIVE_FOLDER) --name player-clusters.csv
	@gdrive upload $(player_stats_final) -p $(OSRS_GDRIVE_FOLDER) --name player-stats.csv
	@gdrive upload $(player_stats_raw) -p $(OSRS_GDRIVE_FOLDER) --name player-stats-raw.csv

## ---- Testing ----

lint:
	@source env/bin/activate && pycodestyle src scripts --ignore=E301,E302,E402,E501
	@echo "code check passed"

test-scrape:
	@source env/bin/activate && cd test && \
	pytest test_scrape.py

test-scripts:
	@source env/bin/activate && cd test && \
	pytest test_scripts.py

build-test-data:
	@source env/bin/activate && \
	bin/dev/build_test_data --base-file $(player_stats) \
	                        --out-file test/data/test-data.csv

## ---- Other ----

start-mongo:
	@bin/start_mongo

ec2-%: # status, start, stop, connect, setup
	@bin/dev/ec2_instance $*

help: ## Print this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
