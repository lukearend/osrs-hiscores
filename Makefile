export SHELL:=/bin/bash

ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

ifneq (,$(wildcard .env))
    include .env
endif

.DEFAULT_GOAL = help

# Top-level ---------------------------------------------------------------------------------------

build: init test download export appdata app ## Build app from downloaded data.

all: init test appdata export upload ## Build repo results from scratch.

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

stats_raw:=$(ROOT)/data/raw/stats-raw
stats:=$(ROOT)/data/interim/stats

scrape: $(stats_raw).csv ## Scrape hiscores data.

clean: $(stats).pkl ## Clean raw scraped dataset.

$(stats_raw).csv:
	@source env/bin/activate && cd scripts && \
	python scrape_hiscores.py --out-file $(stats_raw).tmp --start-rank 1 --stop-rank 2000000 --num-workers 28 \
	                          --log-file $(ROOT)/data/raw/scrape.log --log-level INFO --vpn && \
	mv $(stats_raw).tmp $(stats_raw).csv

$(stats).pkl: $(stats_raw).csv
	@source env/bin/activate && python scripts/clean_raw_data.py --in-file $< --out-file $@

# Clustering and analysis -------------------------------------------------------------------------

splits:=$(ROOT)/ref/skill-splits.json
params:=$(ROOT)/ref/split-params.json
clusterids:=$(ROOT)/data/interim/clusterids
centroids:=$(ROOT)/data/interim/centroids
quartiles:=$(ROOT)/data/interim/quartiles
xyz:=$(ROOT)/data/interim/xyz

cluster: $(clusterids).pkl $(centroids).pkl ## Cluster players by account stats.

quartiles: $(quartiles).pkl ## Compute cluster stat quartiles.

dimreduce: $(xyz).pkl ## Reduce cluster centroids to 3D.

$(clusterids).pkl $(centroids).pkl: $(stats).pkl
	@source env/bin/activate && cd scripts && \
	python cluster_players.py --in-file $< --out-clusterids $(clusterids).pkl --out-centroids $(centroids).pkl \
	                          --splits-file $(splits) --params-file $(params) --verbose

$(quartiles).pkl: $(stats).pkl $(clusterids).pkl
	@source env/bin/activate && cd scripts && \
	python compute_quartiles.py --stats-file $(word 1,$^) --clusterids-file $(word 2,$^) --out-file $@

$(xyz).pkl: $(centroids).pkl
	@source env/bin/activate && cd scripts && \
	python dim_reduce_clusters.py --in-file $< --out-file $@ --params-file $(params)

# Dash application --------------------------------------------------------------------------------

app_data:=$(ROOT)/data/interim/appdata
mongo_url:=$(or $(OSRS_MONGO_URI), localhost:27017)
app_coll:=$(or $(OSRS_APPDATA_COLL), players)

appdata: $(app_data).pkl ## Build final application data.

$(app_data).pkl: $(stats).pkl $(clusterids).pkl $(centroids).pkl $(quartiles).pkl $(xyz).pkl
	@source env/bin/activate && cd scripts && \
	python build_app.py --splits-file $(splits) --stats-file $(word 1,$^) \
	                    --clusterids-file $(word 2,$^) --centroids-file $(word 3,$^) \
	                    --quartiles-file $(word 4,$^) --xyz-file $(word 5,$^) \
                        --out-file $@ --mongo-url $(mongo_url) --collection $(app_coll)

app: ## Run application.
	@bin/start_mongo && source env/bin/activate && \
	python app --mongo-url $(mongo_url) --collection $(app_coll) --data-file $(app_data).pkl --debug

# Importing and exporting data --------------------------------------------------------------------

s3_bucket:=$(or, $(OSRS_DATASET_BUCKET), osrshiscores)
stats_final:=$(ROOT)/data/final/player-stats.csv
clusterids_final:=$(ROOT)/data/final/player-clusterids.csv
centroids_final:=$(ROOT)/data/final/cluster-centroids.csv

download: ## Download scraped and clustered data.
	@source env/bin/activate && bin/dev && \
	download_dataset $(s3_bucket) $(stats).pkl $(clusterids).pkl $(centroids).pkl

upload: push-aws push-gdrive

export: $(stats_final) $(clusterids_final) $(centroids_final) ## Export result files to CSV.

$(stats_final): $(stats).pkl
	@source env/bin/activate && bin/dev/pkl_to_csv $< $@ --type players

$(clusterids_final): $(clusterids).pkl
	@source env/bin/activate && bin/dev/pkl_to_csv $< $@ --type clusterids

$(centroids_final): $(centroids).pkl
	@source env/bin/activate && bin/dev/pkl_to_csv $< $@ --type centroids

push-aws: $(stats_raw).csv $(stats).pkl $(clusterids).pkl $(centroids).pkl $(app_data).pkl
	aws s3 cp $(appdata) "s3://$(OSRS_APPDATA_BUCKET)/$(OSRS_APPDATA_S3_KEY)" &&
	aws s3 cp $(centroids) "s3://$(OSRS_DATASET_BUCKET)/centroids.pkl" &&
	aws s3 cp $(clusterids) "s3://$(OSRS_DATASET_BUCKET)/clusterids.pkl" &&
	aws s3 cp $(stats) "s3://$(OSRS_DATASET_BUCKET)/stats.pkl"

push-gdrive: $(stats_raw).csv $(stats_final).csv $(centroids_final).csv $(clusterids_final).csv
	gdrive upload "$centroids" -p $OSRS_GDRIVE_DIR --name cluster-centroids.csv &&
	gdrive upload "$clusterids" -p $OSRS_GDRIVE_DIR --name player-clusters.csv &&
	gdrive upload "$stats" -p $OSRS_GDRIVE_DIR --name player-stats.csv &&
	gdrive upload "$stats_raw" -p $OSRS_GDRIVE_DIR --name stats-raw.csv &&

# Other utilities ---------------------------------------------------------------------------------

ec2-%: # status, start, stop, connect, setup
	@source .env && cd bin/dev/ec2_instance $*

test: lint ## Run test suite.
	@source env/bin/activate && pytest test

lint:
	@source env/bin/activate && pycodestyle app src --ignore=E301,E302,E303,E402,E501 && \
	echo "code check passed"

help: ## Print this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
