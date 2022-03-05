export SHELL:=/bin/bash
export AMBER_LICENSE_ID:=luke-dev

ifneq (,$(wildcard ./.env))
	include .env
	export
endif

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
DATA_RAW:=$(ROOT_DIR)/data/raw
DATA_TMP:=$(ROOT_DIR)/data/interim
DATA_FINAL:=$(ROOT_DIR)/data/processed
TEST_DIR:=$(ROOT_DIR)/test

.DEFAULT_GOAL := help

all: env scrape cluster dimreduce app # Scrape data, process it and build final application.
build: env download test dimreduce app # Build final application from downloaded pre-scraped data.
run:
	@source env/bin/activate && OSRS_APP_ENV=development python app

.PHONY: all build clean run

# Setup -------------------------------------------------------------------------------------------
env: env-init env-build ## Setup project dependencies.

env-init:
	@python3 -m venv env

env-build:
	@echo "building virtual environment..."
	@source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info

env-clean:
	rm -rf env

clean: env-clean scrape-clean cluster-clean dimreduce-clean app-clean # Remove all generated results.

.PHONY: init env env-clean

# Data scraping -----------------------------------------------------------------------------------
scrape: $(DATA_FINAL)/player-stats.csv ## Run data scrape of OSRS hiscores.

$(DATA_RAW)/usernames-raw.csv: # note: depends on ExpressVPN and expresso (CLI to ExpressVPN)
	@source env/bin/activate && \
	cd src/scrape && \
	until python scrape_usernames.py $@ ; do \
		echo "resetting vpn connection..." ; \
		loc=`expresso locations | grep -- '- USA - ' | sed 's/^.*(//;s/)$$//' | shuf -n 1` && \
		expresso connect --change $$loc ; \
	done

$(DATA_TMP)/usernames.csv: $(DATA_RAW)/usernames-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python cleanup_usernames.py $< $@

$(DATA_RAW)/stats-raw.csv: $(DATA_TMP)/usernames.csv
	@source env/bin/activate && \
	cd src/scrape && \
	until python scrape_stats.py $< $@; do \
		echo "resetting vpn connection..."; \
		loc=`expresso locations | grep -- '- USA - ' | sed 's/^.*(//;s/)$$//' | shuf -n 1` && \
		expresso connect --change $$loc; \
	done

$(DATA_FINAL)/player-stats.csv: $(DATA_RAW)/stats-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python cleanup_stats.py $(DATA_RAW)/stats-raw.csv $@

scrape-clean: # Keep raw dump files.
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_FINAL)/player-stats.csv

scrape-clobber: # Delete all files from scraping process.
	rm -f $(DATA_RAW)/usernames-raw.csv
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_RAW)/stats-raw.csv
	rm -f $(DATA_FINAL)/player-stats.csv

.PHONY: scrape scrape-clean scrape-clobber
.PRECIOUS: $(DATA_RAW)/usernames-raw.csv $(DATA_RAW)/stats-raw.csv

# Clustering --------------------------------------------------------------------------------------
cluster: $(DATA_FINAL)/player-clusters.csv ## Cluster players according to scraped stats.

$(DATA_FINAL)/cluster-centroids.csv:
	@source env/bin/activate && \
	cd src/models && python fit_clusters.py $(DATA_FINAL)/player-stats.csv $@

$(DATA_FINAL)/player-clusters.csv: $(DATA_FINAL)/cluster-centroids.csv
	@source env/bin/activate && \
	cd src/models && python cluster_players.py $(DATA_FINAL)/player-stats.csv $< $@

cluster-clean:
	rm -f $(DATA_FINAL)/cluster-centroids.csv
	rm -f $(DATA_FINAL)/player-clusters.csv

.PHONY: cluster cluster-clean

# Dimensionality reduction ------------------------------------------------------------------------
dimreduce: $(DATA_TMP)/clusters_xyz.pkl ## Reduce cluster dimensionality for visualization.

$(DATA_TMP)/clusters_xyz.pkl:
	@source env/bin/activate && \
	cd src/models && python dim_reduce_clusters.py $(DATA_FINAL)/cluster-centroids.csv $@

dimreduce-clean:
	rm -f $(DATA_TMP)/clusters_xyz.pkl

.PHONY: dimreduce dimreduce-clean

# Application -------------------------------------------------------------------------------------
app: $(DATA_FINAL)/app_data.pkl mongo build-db ## Build data file and database for visualization app.

$(DATA_TMP)/cluster_analytics.pkl:
	@source env/bin/activate && \
	cd src/results && python postprocess_clusters.py $(DATA_FINAL)/player-stats.csv $(DATA_FINAL)/player-clusters.csv $@

$(DATA_FINAL)/app_data.pkl: $(DATA_FINAL)/cluster-centroids.csv $(DATA_TMP)/cluster_analytics.pkl $(DATA_TMP)/clusters_xyz.pkl
	@source env/bin/activate && \
	cd src/results && python build_app_data.py $^ $@

app-clean:
	rm -rf volume
	rm -f $(DATA_FINAL)/app_data.pkl

.PHONY: app app-clean

# Data import/export ------------------------------------------------------------------------------

upload-appdata:
	cd bin && ./upload_appdata

upload-dataset:
	cd bin && ./upload_dataset

download: ## Download processed dataset from S3.
	@source env/bin/activate && \
	cd bin && OSRS_DATASET_S3BUCKET=osrshiscores ./download_dataset

build-db:
	@source env/bin/activate && \
	cd bin && OSRS_MONGO_URI=localhost:27017 \
	./build_database $(DATA_FINAL)/player-stats.csv $(DATA_FINAL)/player-clusters.csv players

mongo: ## Launch a Mongo instance at localhost:27017 using Docker.
	@docker pull mongo
	@mkdir -p mongo && \
	docker stop osrs-hiscores > /dev/null 2>&1 ; \
	docker run --rm -d --name osrs-hiscores \
	-v volume:/data/db -p 27017:27017 mongo
	@echo -n "starting... " && sleep 2 && echo -e "done"

.PHONY: upload-appdata upload-dataset download mongo build-db

# Testing -----------------------------------------------------------------------------------------

lint: ## Run code style checker.
	@source env/bin/activate && \
	pycodestyle app src --ignore=E501,E302 && \
	echo "code check passed"

$(TEST_DIR)/data/player-stats-10000.csv: # small subsample of the full dataset for unit testing
	@source env/bin/activate && \
	cd test && python build_stats_small.py $(DATA_FINAL)/player-stats.csv $@

test: lint $(TEST_DIR)/data/player-stats-10000.csv ## Run unit tests for data pipeline.
	@source env/bin/activate && \
	pytest test -sv

ec2-%: ## EC2 instance: status, start, stop, connect, setup, docker-start
	@cd bin && ./ec2_instance $*

.PHONY: lint test ec2-%

# Other -------------------------------------------------------------------------------------------
vim-binding: # install vim keybindings for notebooks
	@source env/bin/activate && \
	jupyter contrib nbextensions install && \
	cd $(shell jupyter --data-dir)/nbextensions && \
	git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding || \
	cd vim_binding && git pull

nbextensions: vim-binding # a few nice notebook extensions
	jupyter nbextension enable vim_binding/vim_binding
	jupyter nbextension enable rubberband/main
	jupyter nbextension enable toggle_all_line_numbers/main
	jupyter nbextension enable varInspector/main

notebook: nbextensions ## Start a local jupyter notebook server.
	@source env/bin/activate && \
	jupyter notebook

help: ## Show this help.
	@grep -E '^[0-9a-zA-Z%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: vim-binding nbextensions notebook help
