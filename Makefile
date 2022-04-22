export SHELL:=/bin/bash

ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

ifneq (,$(wildcard .env))
    include .env
	export
endif

.DEFAULT_GOAL = help

# Top-level ---------------------------------------------------------------------------------------

build: init test download export quartiles dimreduce appdata app ## Build app from downloaded data.

all: init test scrape clean cluster quartiles dimreduce appdata export upload ## Build repo results from scratch.

app: mongo-start ## Run visualization app.
	@source env/bin/activate && python3 app

init: env mongo ## Initialize repository.
	mkdir -p data/raw data/interim data/final

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
	@source env/bin/activate && cd scripts && \
	python clean_raw_data.py --in-file $< --out-file $@

# Clustering and dimensionality reduction ---------------------------------------------------------

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

# Application data/database -----------------------------------------------------------------------

app_data:=$(ROOT)/data/interim/appdata
mongo_url:=$(or $(OSRS_MONGO_URI), localhost:27017)
app_coll:=$(or $(OSRS_MONGO_COLL), players)

appdata: $(app_data).pkl ## Build final application data.

mongo:
	docker pull mongo

mongo-start:
	@cd bin && ./start_mongo

$(app_data).pkl: $(stats).pkl $(clusterids).pkl $(centroids).pkl $(quartiles).pkl $(xyz).pkl
	@source env/bin/activate && cd scripts && \
	python build_app.py --stats-file $(word 1,$^) --clusterids-file $(word 2,$^) --centroids-file $(word 3,$^)
	                    --quartiles-file $(word 4,$^) --xyz-file $(word 5,$^) --out-file $@
	                    --mongo-url $(mongo_url) --collection $(app_coll)

# Importing and exporting data --------------------------------------------------------------------

stats_final:=$(ROOT)/data/final/player-stats.csv
clusterids_final:=$(ROOT)/data/final/player-clusterids.csv
centroids_final:=$(ROOT)/data/final/cluster-centroids.csv

export: $(stats_final) $(clusterids_final) $(centroids_final) ## Export stats and clustering results to CSV.

download: ## Download raw stats and clustering results.
	@source env/bin/activate && cd bin && \
	./download_dataset $(stats_raw).csv $(stats).pkl $(clusterids).pkl $(centroids).pkl

upload: ## Upload
	@cd bin/dev && ./push_artifacts $(stats_raw).csv $(stats).pkl $(clusterids).pkl $(centroids).pkl \
                                    $(app_data).pkl $(stats_final) $(clusterids_final) $(centroids_final)

$(stats_final).csv: $(stats).pkl
	@source env/bin/activate && cd bin/dev && \
	./pkl_to_csv $< $@ --type players

$(centroids_final).csv: $(centroids).pkl
	@source env/bin/activate && cd bin/dev && \
	./pkl_to_csv $< $@ --type centroids

$(clusterids_final).csv: $(clusterids).pkl
	@source env/bin/activate && cd bin/dev && \
	./pkl_to_csv $< $@ --type clusterids

# Other utilities ---------------------------------------------------------------------------------

ec2-%: # options: status, start, stop, connect, setup
	@cd bin/dev && ./ec2_instance $*

test: lint ## Run test suite.
	@source env/bin/activate && pytest test

lint:
	@source env/bin/activate && pycodestyle app src --ignore=E301,E302,E303,E402,E501 && \
	echo "code check passed"

help: ## Print this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
