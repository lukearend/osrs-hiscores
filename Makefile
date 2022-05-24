export SHELL := /bin/bash
ROOT := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

include .env
export

.DEFAULT_GOAL = help

user: init test download postprocess build-app run-app
nightly: init test scrape cluster export postprocess build-app push-app deploy-dev
final: init scrape cluster export upload-data postprocess build-app push-app deploy-prod

## ---- Top-level ----

download: download-pkl export-csv                  ## Download pre-scraped data and clustering results.
upload-data: upload-pkl upload-csv                    ## Upload finalized dataset.
upload-app: app-blob app-db-prod push-app-blob

## ---- Setup ----

init: env pull-mongo  ## Setup repository and install dependencies.
	mkdir -p data/raw data/interim data/final

env:
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt
	rm -rf *.egg-info

pull-mongo:
	docker pull mongo

## ---- Scraping and cleaning ----

scrape: scrape-hiscores clean-scraped-data  ## Create account stats dataset from the OSRS hiscores.

player_stats_raw := $(ROOT)/data/raw/player-stats-raw.csv
player_stats := $(ROOT)/data/interim/player-stats.pkl

scrape-hiscores: $(player_stats_raw)

$(player_stats_raw):
	echo $(player_stats_raw)
	@source env/bin/activate && cd scripts && \
	python scrape_hiscores.py --start-rank 1 --stop-rank 2000000 --num-workers 28 \
	                          --log-file $(ROOT)/data/raw/scrape.log --log-level INFO \
	                          --out-file $(player_stats_raw).tmp --vpn
	mv $(player_stats_raw).tmp $(player_stats_raw)

clean-scraped-data: $(player_stats)
$(player_stats):
	@source env/bin/activate && cd scripts && \
	python clean_raw_data.py --in-file $(player_stats_raw) --out-file $@

.SECONDARY: $(player_stats_raw) # Don't require $(stats_raw) if $(player_stats) already exists.

## ---- Clustering and analysis ----

cluster_ids := $(ROOT)/data/interim/player-clusterids.pkl
cluster_centroids := $(ROOT)/data/interim/cluster-centroids.pkl

cluster: $(cluster_ids) $(cluster_centroids)  ## Cluster players according to account similarity.
$(cluster_ids) $(cluster_centroids):
	@source env/bin/activate && cd scripts && \
	python cluster_players.py --in-file $(player_stats) \
                              --splits-file $(ROOT)/ref/skill-splits.json \
	                          --params-file $(ROOT)/ref/split-params.json \
	                          --out-clusterids $(cluster_ids) \
	                          --out-centroids $(cluster_centroids) \
	                          --verbose

cluster_xyz := $(ROOT)/data/interim/cluster-xyz.pkl
cluster_quartiles := $(ROOT)/data/interim/cluster-quartiles.pkl

postprocess: compute-quartiles dimreduce-clusters     ## Analyze and postprocess clustering results.

dimreduce-clusters: $(cluster_xyz)
$(cluster_xyz):
	@source env/bin/activate && cd scripts && \
	python dim_reduce_clusters.py --params-file $(ROOT)/ref/split-params.json \
	                              --in-file $(cluster_centroids) \
	                              --out-file $@

compute-quartiles: $(cluster_quartiles)
$(cluster_quartiles):
	@source env/bin/activate && cd scripts && \
	python compute_quartiles.py --splits-file $(ROOT)/ref/skill-splits.json \
	                            --stats-file $(player_stats) \
	                            --clusterids-file $(cluster_ids) \
	                            --out-file $@ \

.SECONDARY: $(player_stats_raw) # Don't require $(stats_raw) if $(player_stats) already exists.

## ---- Main application ----

mongo_url := $(or $(OSRS_MONGO_URI), localhost:27017)
app_data := $(ROOT)/data/final/app-data.pkl

run-app: start-mongo  ## Run main application.
	@source env/bin/activate && \
	export OSRS_MONGO_URI=$(mongo_url) && \
	export OSRS_APPDATA_URI=$(app_data) && \
	export OSRS_DISABLE_AUTH=true && \
	python app

build-app: app-blob app-db  ## Build data blob and database needed by main application.

app-blob: $(app_data)
$(app_data):
	@source env/bin/activate && cd scripts && \
	python build_app_data.py --splits-file $(ROOT)/ref/skill-splits.json \
	                         --clusterids-file $(cluster_ids) \
	                         --centroids-file $(cluster_centroids) \
	                         --quartiles-file $(cluster_quartiles) \
	                         --xyz-file $(cluster_xyz) \
	                         --out-file $(app_data)

app-db: start-mongo
	@source env/bin/activate && cd scripts && \
	python build_app_db.py --stats-file $(player_stats) \
	                       --clusterids-file $(cluster_ids) \
	                       --mongo-url $(mongo_url) \
	                       --collection players

push-app:  ## Push finalized app data to the cloud.
	aws s3 cp $(app_data) $(OSRS_APPDATA_URI)
	source env/bin/activate && cd scripts && \
	python build_app_db.py --stats-file $(player_stats) \
	                       --clusterids-file $(cluster_ids) \
	                       --mongo-url $(OSRS_MONGO_URI_PROD) \
	                       --collection players

deploy-dev:
	git push staging refactor-app:master

deploy-prod:
	git push heroku master:master

# ---- Upload and download ----

upload-pkl: upload-centroids-pkl upload-clusterids-pkl upload-stats-pkl
download-pkl: download-centroids-pkl download-clusterids-pkl download-stats-pkl
    # set timestamps in order of file creation
	touch $(player_stats)
	touch $(cluster_ids) $(cluster_centroids)

player_stats_s3      := s3://osrshiscores/player-stats.pkl
cluster_ids_s3       := s3://osrshiscores/player-clusterids.pkl
cluster_centroids_s3 := s3://osrshiscores/cluster-centroids.pkl

upload-stats-pkl:
	aws s3 cp $(player_stats) $(player_stats_s3)

upload-clusterids-pkl:
	aws s3 cp $(cluster_ids) $(cluster_ids_s3)

upload-centroids-pkl:
	aws s3 cp $(cluster_centroids) $(cluster_centroids_s3)

download-stats-pkl:
	@source env/bin/activate && \
	bin/download_s3 --s3-url $(player_stats_s3) --local-file $(player_stats)

download-clusterids-pkl:
	@source env/bin/activate && \
	bin/download_s3 --s3-url $(cluster_ids_s3) --local-file $(cluster_ids)

download-centroids-pkl:
	@source env/bin/activate && \
	bin/download_s3 --s3-url $(cluster_centroids_s3) --local-file $(cluster_centroids)

## ---- Finalization ----

export-csv: export-stats-csv export-clusterids-csv export-centroids-csv  ## Export finalized dataset to CSV.

player_stats_final      := $(ROOT)/data/final/player-stats.csv
cluster_ids_final       := $(ROOT)/data/final/player-clusterids.csv
cluster_centroids_final := $(ROOT)/data/final/cluster-centroids.csv

export-stats-csv:      $(player_stats_final)
export-clusterids-csv: $(cluster_ids_final)
export-centroids-csv:  $(cluster_centroids_final)

$(player_stats_final): $(player_stats)
	@source env/bin/activate && \
	bin/pkl_to_csv --pkl-file $< --csv-file $@ --type players

$(cluster_ids_final): $(cluster_ids)
	@source env/bin/activate && \
	bin/pkl_to_csv --pkl-file $< --csv-file $@ --type clusterids

$(cluster_centroids_final): $(cluster_centroids)
	@source env/bin/activate && \
	bin/pkl_to_csv --pkl-file $< --csv-file $@ --type centroids

upload-csv:
	gdrive upload $(player_stats_raw) -p $(OSRS_GDRIVE_FOLDER) --name player-stats-raw.csv
	gdrive upload $(player_stats_final) -p $(OSRS_GDRIVE_FOLDER) --name player-stats.csv
	gdrive upload $(cluster_ids_final) -p $(OSRS_GDRIVE_FOLDER) --name player-clusters.csv
	gdrive upload $(cluster_centroids_final) -p $(OSRS_GDRIVE_FOLDER) --name cluster-centroids.csv

## ---- Testing ----

test: lint test-units test-system  ## Run test suite.

lint:
	@source env/bin/activate && pycodestyle src scripts --ignore=E301,E302,E402,E501
	@echo "code check passed"

test-units:
	@source env/bin/activate && pytest test

test-system:
	@: # todo: run bash script which does a small scrape, analysis, and run-app

build-test-data:
	@source env/bin/activate && \
	bin/build_test_data --base-file $(player_stats) \
	                        --out-file test/data/test-data.csv

## ---- Other ----

touch-pipeline:
	touch player-stats-raw.csv


start-mongo:
	@bin/start_mongo

ec2-%: # status, start, stop, connect, setup
	@bin/ec2_instance $*

help: ## Print this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
