export SHELL := /bin/bash

ROOT := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

ifneq (,$(wildcard .env))
    include .env
endif

.DEFAULT_GOAL = help

# Top-level ---------------------------------------------------------------------------------------

build: init test download export appdata app ## Build app from downloaded data.

all: init test scrape cluster appdata export upload ## Build repo results from scratch.

init: env ## Initialize repository.
	mkdir -p data/raw data/interim data/final
	docker pull mongo

env:
	@echo "building virtual environment..."
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt
	rm -rf *.egg-info

# Data scraping and cleaning ----------------------------------------------------------------------

stats_raw   := $(ROOT)/data/raw/player-stats-raw.csv
stats       := $(ROOT)/data/interim/player-stats.pkl
stats_final := $(ROOT)/data/final/player-stats.csv

scrape: $(stats_raw) ## Scrape hiscores data.

clean: $(stats) ## Clean raw scraped dataset.

$(stats_raw):
	@source env/bin/activate && cd scripts && \
	python src.scrape --out-file $(stats_raw).tmp --start-rank 1 --stop-rank 2000000 --num-workers 28 \
	                  --log-file $(ROOT)/data/raw/scrape.log --log-level INFO --vpn && \
	mv $(stats_raw).tmp $(stats_raw)

$(stats): $(stats_raw)
	@source env/bin/activate && python scripts/clean_raw_data.py --in-file $< --out-file $@

.SECONDARY: $(stats_raw) # don't require $(stats_raw) if $(stats) already exists

# Clustering and analysis -------------------------------------------------------------------------

splits := $(ROOT)/ref/skill-splits.json
params := $(ROOT)/ref/split-params.json

clusterids := $(ROOT)/data/interim/player-clusterids.pkl
centroids  := $(ROOT)/data/interim/cluster-centroids.pkl
quartiles  := $(ROOT)/data/interim/cluster-quartiles.pkl
xyz        := $(ROOT)/data/interim/cluster-xyz.pkl

clusterids_final := $(ROOT)/data/final/player-clusterids.csv
centroids_final  := $(ROOT)/data/final/cluster-centroids.csv

cluster: $(clusterids) $(centroids) ## Cluster players by account stats.

quartiles: $(quartiles) ## Compute cluster stat quartiles.

dimreduce: $(xyz) ## Reduce cluster centroids to 3D.

$(clusterids) $(centroids): $(stats)
	@source env/bin/activate && cd scripts && \
	python cluster_players.py --in-file $< --out-clusterids $(clusterids) --out-centroids $(centroids) \
	                          --splits-file $(splits) --params-file $(params) --verbose

$(quartiles): $(stats) $(clusterids)
	@source env/bin/activate && cd scripts && \
	python compute_quartiles.py --stats-file $(word 1,$^) --clusterids-file $(word 2,$^) \
	                            --splits-file $(splits) --out-file $@

$(xyz): $(centroids)
	@source env/bin/activate && cd scripts && \
	python dim_reduce_clusters.py --in-file $< --out-file $@ --params-file $(params)

# Dash application --------------------------------------------------------------------------------

mongo_url    := $(or $(OSRS_MONGO_URI), localhost:27017)
appdata_coll := $(or $(OSRS_APPDATA_COLL), appdata)
appdata      := $(or $(OSRS_APPDATA_FILE), $(ROOT)/data/interim/appdata.pkl)

appdata: $(appdata) ## Build final application data.

app: ## Run application.
	@source env/bin/activate && bin/start_mongo && \
	export OSRS_MONGO_URI=$(mongo_url) && \
	export OSRS_APPDATA_COLL=$(appdata_coll) && \
	export OSRS_APPDATA_FILE=$(appdata) && \
	python app.py

$(appdata): $(stats) $(clusterids) $(centroids) $(quartiles) $(xyz)
	@source env/bin/activate && bin/start_mongo && cd scripts && \
	python build_app.py --splits-file $(splits) --stats-file $(word 1,$^) \
	                    --clusterids-file $(word 2,$^) --centroids-file $(word 3,$^) \
	                    --quartiles-file $(word 4,$^) --xyz-file $(word 5,$^) \
                        --out-file $@ --mongo-url $(mongo_url) --collection $(appdata_coll)

# Importing and exporting data --------------------------------------------------------------------

export: $(stats_final) $(clusterids_final) $(centroids_final) ## Export final results to CSV.

$(stats_final): $(stats)
	@source env/bin/activate && bin/pkl_to_csv --in-file $< --out-file $@ --type players

$(clusterids_final): $(clusterids)
	@source env/bin/activate && bin/pkl_to_csv --in-file $< --out-file $@ --type clusterids

$(centroids_final): $(centroids)
	@source env/bin/activate && bin/pkl_to_csv --in-file $< --out-file $@ --type centroids

dataset_bucket := osrshiscores

upload: push-aws push-gdrive

push-aws: $(stats_raw) $(stats) $(clusterids) $(centroids) $(appdata)
	@aws s3 cp $(appdata).pkl "s3://$(OSRS_APPDATA_BUCKET)/$(OSRS_APPDATA_S3_KEY)"
	@aws s3 cp $(centroids) "s3://$(dataset_bucket)/centroids.pkl"
	@aws s3 cp $(clusterids) "s3://$(dataset_bucket)/clusterids.pkl"
	@aws s3 cp $(stats) "s3://$(dataset_bucket)/stats.pkl"

push-gdrive: $(stats_raw) $(stats_final) $(centroids_final) $(clusterids_final)
	@gdrive upload $(word 3,$^) -p $(OSRS_GDRIVE_FOLDER) --name cluster-centroids.csv
	@gdrive upload $(word 4,$^) -p $(OSRS_GDRIVE_FOLDER) --name player-clusters.csv
	@gdrive upload $(word 2,$^) -p $(OSRS_GDRIVE_FOLDER) --name player-stats.csv
	@gdrive upload $(word 1,$^) -p $(OSRS_GDRIVE_FOLDER) --name stats-raw.csv

download: ## Download scraped and clustered data.
	@source env/bin/activate && bin/download_dataset $(dataset_bucket) $(stats) $(clusterids) $(centroids)

# Other utilities ---------------------------------------------------------------------------------

ec2-%: # status, start, stop, connect, setup
	@bin/dev/ec2_instance $*

testdata: $(stats)
	@source env/bin/activate && bin/dev/build_test_data --in-file $< --out-file test/data/test-data.csv

test: lint ## Run test suite.
	@source env/bin/activate && bin/start_mongo && pytest test

lint:
	@source env/bin/activate && pycodestyle src scripts --ignore=E301,E302,E303,E402,E501
	@echo "code check passed"

help: ## Print this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
