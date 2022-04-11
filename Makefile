export SHELL:=/bin/bash
ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
ifneq (,$(wildcard .env))
    include .env
	export
endif
.DEFAULT_GOAL = help

build: init test download analytics buildapp run ## build repo from downloaded data

dev: init test dataset analytics buildapp upload

run: mongo-start ## run final app
	@source env/bin/activate && python3 app

# Setup -------------------------------------------------------------------------------------------

init: env mongo datadir ## initialize repository

env:
	echo "building virtual environment..."
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt
	rm -rf *.egg-info

mongo:
	@docker pull mongo

datadir:
	mkdir -p data && cd data && mkdir -p raw interim final

start_rank  :=$(or $(START_RANK), 1)
stop_rank   :=$(or $(STOP_RANK), 2000000)
kmeans_k    :=$(or $(KMEANS_K), 25)
umap_nn     :=$(or $(UMAP_NN), 10)
umap_mindist:=$(or $(UMAP_MINDIST), 0.25)

params: ## print default parameters
	@printf "running with parameters (set via these env vars):\n\n"
	@printf "  start rank: %-10s  (START_RANK)\n" $(start_rank)
	@printf "  stop rank: %-11s  (STOP_RANK)\n" $(stop_rank)
	@printf "  kmeans k = %-11s  (KMEANS_K)\n" $(kmeans_k)
	@printf "  umap n_neighbors = %-4s (UMAP_NN)\n" $(umap_nn)
	@printf "  umap min_dist = %-6s  (UMAP_MINDIST)\n\n" $(umap_mindist)

stats_raw :=$(ROOT)/data/raw/stats-raw-$(start_rank)-$(stop_rank)
stats     :=$(ROOT)/data/interim/stats-$(start_rank)-$(stop_rank)
centroids :=$(ROOT)/data/interim/centroids-$(kmeans_k)
clusterids:=$(ROOT)/data/interim/clusterids-$(kmeans_k)
quartiles :=$(ROOT)/data/interim/quartiles-$(kmeans_k)
xyz       :=$(ROOT)/data/interim/xyz-$(kmeans_k)-$(umap_nn)-$(umap_mindist)
appdata   :=$(ROOT)/data/interim/appdata-$(kmeans_k)-$(umap_nn)-$(umap_mindist)
appcoll   :=players

# Main targets ------------------------------------------------------------------------------------

dataset: scrape clean cluster

scrape: $(stats_raw).csv ## scrape hiscores data

clean: $(stats).pkl ## clean raw scraped dataset

cluster: $(clusterids).pkl $(centroids).pkl ## cluster players by account stats

analytics: quartiles dimreduce buildapp

quartiles: $(quartiles).pkl ## compute cluster stat quartiles

dimreduce: $(xyz).pkl ## reduce cluster centroids to 3D

buildapp: $(appdata).pkl ## build final application data

# Data pipeline -----------------------------------------------------------------------------------

$(stats_raw).csv:
	@source env/bin/activate && cd scripts && \
	if python scrape_hiscores.py --out-file $(stats_raw).tmp \
	    --start-rank $(start_rank) --stop-rank $(stop_rank) --num-workers 28 \
	    --log-file $(ROOT)/data/raw/scrape-$(start_rank)-$(stop_rank).log \
	    --log-level INFO --vpn ; \
	then \
		 mv $(stats_raw).tmp $(stats_raw).csv ; \
	fi

$(stats).pkl: $(stats_raw).csv
	@source env/bin/activate && cd scripts && \
	python clean_raw_data.py --in-file $< --out-file $@

$(clusterids).pkl $(centroids).pkl: $(stats).pkl
	@source env/bin/activate && cd scripts && \
	python cluster_players.py --n-clusters $(kmeans_k) --verbose \
	                          --in-file $< \
	                          --out-clusterids $(clusterids).pkl \
	                          --out-centroids $(centroids).pkl

$(quartiles).pkl: $(stats).pkl $(clusterids).pkl
	@source env/bin/activate && cd scripts && \
	python compute_quartiles.py --stats-file $(word 1,$^) \
                                --clusterids-file $(word 2,$^) \
                                --out-file $@

$(xyz).pkl: $(centroids).pkl
	@source env/bin/activate && cd scripts && \
	python dim_reduce_clusters.py --in-file $< --out-file $@ \
	                              --n-neighbors $(umap_nn) --min-dist $(umap_mindist)

$(appdata).pkl: $(stats).pkl $(clusterids).pkl $(centroids).pkl $(quartiles).pkl $(xyz).pkl
	@source env/bin/activate && cd scripts && \
	python build_app.py --stats-file $(word 1,$^) \
	                    --clusterids-file $(word 2,$^) \
	                    --centroids-file $(word 3,$^) \
	                    --quartiles-file $(word 4,$^) \
	                    --xyz-file $(word 5,$^) \
	                    --out-file $@ --mongo-url localhost:27017 \
	                    --collection $(appcoll) --nclusters $(kmeans_k)

# Upload/download ---------------------------------------------------------------------------------

stats_final     :=$(ROOT)/data/final/player-stats
clusterids_final:=$(ROOT)/data/final/player-clusterids
centroids_final :=$(ROOT)/data/final/cluster-centroids

export: $(stats_final).csv $(clusterids_final).csv $(centroids_final).csv

upload:
	@cd bin/dev && ./push_artifacts $(stats_raw).csv $(stats_final).csv $(centroids_final).csv $(clusterids_final).csv

download: ## Download player stats and clustering results data.
	@source env/bin/activate && cd bin && \
	./download_dataset $(stats_raw).csv $(stats_final).pkl $(centroids_final).pkl $(clusterids_final).pkl
	./export_dataset $(stats_final).pkl $(stats).csv \
	                 $(clusterids_final).pkl $(clusterids).csv \
	                 $(centroids_final).pkl $(centroids).csv

finalize: $(stats_final).csv $(centroids_final).csv $(clusterids_final).csv

$(stats_final).csv $(centroids_final).csv $(clusterids_final).csv: $(stats).pkl $(clusterids).pkl $(centroids).pkl
	@source env/bin/activate && cd bin/dev && \
	cp $(stats).pkl $(stats_final).pkl && \
	cp $(clusterids).pkl $(clusterids_final).pkl && \
	cp $(centroids).pkl $(centroids_final).pkl && \
	./export_dataset $(stats_final).pkl $(stats_final).csv \
					 $(clusterids_final).pkl $(clusterids_final).csv \
					 $(centroids_final).pkl $(centroids_final).csv ; \

# General development -----------------------------------------------------------------------------

ec2-%: # options: status, start, stop, connect, setup
	@cd bin/dev && ./ec2_instance $*

mongo-start:
	@cd bin && ./start_mongo

test-data:
	source env/bin/activate && cd bin/dev && \
	./build_testdata --in-file $(stats).pkl --out-file $(ROOT)/test/data/test-data.csv

test: lint ## Run test suite.
	@source env/bin/activate && pytest test

lint:
	@source env/bin/activate && pycodestyle app src --ignore=E301,E302,E402,E501 && \
	echo "code check passed"

help:
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
