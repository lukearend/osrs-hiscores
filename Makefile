export SHELL:=/bin/bash
ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
ifneq (,$(wildcard .env))
    include .env
	export
endif

start_rank:=$(or $(START_RANK), 1000001)
stop_rank:=$(or $(STOP_RANK), 1001000)
kmeans_k:=$(or $(KMEANS_K), 25)
umap_nn:=$(or $(UMAP_NN), 10)
umap_mindist:=$(or $(UMAP_MINDIST), 0.25)

raw_stats:=$(ROOT)/data/raw/stats-raw-$(start_rank)-$(stop_rank)
stats:=$(ROOT)/data/final/stats-$(start_rank)-$(stop_rank)
centroids:=$(ROOT)/data/final/centroids-$(k)
clusterids:=$(ROOT)/data/final/clusterids-$(k)
quartiles:=$(ROOT)/data/interim/quartiles-$(k)
xyz:=$(ROOT)/data/interim/xyz-$(k)-$(nn)-$(mindist)
appdata:=$(ROOT)/data/final/appdata-$(k)-$(nn)-$(mindist)
appcoll:=players

.DEFAULT_GOAL = help

build: init download test cluster analytics buildapp run

dev: init test scrape clean cluster analytics buildapp upload

run: mongo-start
	@source env/bin/activate && python3 app

init: env mongo

env:
	echo "building virtual environment..."
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt
	rm -rf *.egg-info

download:
	@source env/bin/activate && cd bin && \
	./download_dataset $(stats_raw).pkl $(stats).pkl $(centroids).pkl $(clusterids).pkl

test: lint
	@source env/bin/activate && cd test && pytest . -sv --asyncio-mode=strict

params: ## print default parameters
	@echo "running with parameters:"
	@printf "  start rank: %-14s  (START_RANK)\n" $(start_rank)
	@printf "  stop rank: %-15s  (STOP_RANK)\n" $(stop_rank)
	@printf "  kmeans k = %-15s  (KMEANS_K)\n" $(kmeans_k)
	@printf "  umap n_neighbors = %-8s (UMAP_NN)\n" $(umap_nn)
	@printf "  umap min_dist = %-10s  (UMAP_MINDIST)\n" $(umap_mindist)

scrape: $(raw_stats).csv ## scrape hiscores

clean: $(stats).pkl

$(raw_stats).csv:
	@source env/bin/activate && cd scripts && \
	if python scrape_hiscores.py --out-file $(raw_stats).tmp \
	    --start-rank $(start_rank) --stop-rank $(stop_rank) --num-workers 28 \
	    --log-file $(ROOT)/data/raw/scrape-$(start_rank)-$(stop_rank).log \
	    --log-level INFO --vpn ; \
	then \
		 mv $(raw_stats).tmp $(raw_stats).csv ; \
	fi

$(stats).pkl: $(raw_stats).csv ## clean raw dataset
	@source env/bin/activate && cd scripts && \
	python clean_raw_data.py --in-file $(raw_stats).csv --out-file $(stats).pkl

cluster: ## cluster players
	@source env/bin/activate && cd scripts && \
	python cluster_players.py --nclusters $* --verbose \
	                          --in-file $(stats)-$*.pkl \
							  --out-clusterids $(clusterids)-$*.pkl \
                              --out-centroids $(centroids)-$*.pkl

analytics: quartiles dimreduce

quartiles: ## compute cluster quartiles
	@source env/bin/activate && cd scripts && \
	python compute_quartiles.py

dimreduce: ## reduce centroid to 3D
	@source env/bin/activate && cd scripts && \
	python dim_reduce_clusters.py

buildapp: appdata appdb

appdata: ## build app data file
	@source env/bin/activate && cd scripts && \
	python build_app_data.py

appdb: ## build app database
	@source env/bin/activate && cd scripts && \
	python build_database.py

dataset:
	@source env/bin/activate && cd scripts && \
	python export_dataset_csv.py

upload:
	@cd bin/dev && ./push_artifacts $(stats_raw) $(stats).csv $(centroids).csv $(clusterids).csv

mongo:
	@docker pull mongo

mongo-start:
	@cd bin && ./start_mongo

ec2-%: # options: status, start, stop, connect, setup
	@cd bin/dev && ./ec2_instance $*

lint:
	@source env/bin/activate && pycodestyle app src --ignore=E301,E302,E501 && \
	echo "code check passed"

help:
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: app env test
