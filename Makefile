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
GDRIVE_DIR:=***REMOVED***
S3_BUCKET:=osrshiscores

.DEFAULT_GOAL := help

all: init scrape cluster dimreduce app # Scrape data, process it and build application from scratch.
build: init download dimreduce app # Build final application from downloaded data.
clean: env-clean scrape-clean cluster-clean dimreduce-clean app-clean
test: lint app-run

# Setup -------------------------------------------------------------------------------------------
init: env nbextensions ## Setup project dependencies.

env:
	@echo "building virtual environment..."
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info

env-clean:
	rm -rf env

.PHONY: all clean init env-clean

# Data scraping -----------------------------------------------------------------------------------
scrape: $(DATA_FINAL)/stats.csv ## Run data scrape of OSRS hiscores.

$(DATA_RAW)/usernames-raw.csv:
	@source env/bin/activate && \
	cd src/scrape && \
	until python3 scrape_usernames.py $@ ; do \
		echo "resetting vpn connection..." ; \
		loc=`expresso locations | grep -- '- USA - ' | sed 's/^.*(//;s/)$$//' | shuf -n 1` && \
		expresso connect --change $$loc ; \
	done

$(DATA_TMP)/usernames.csv: $(DATA_RAW)/usernames-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python3 cleanup_usernames.py $< $@

$(DATA_RAW)/stats-raw.csv: $(DATA_TMP)/usernames.csv
	@source env/bin/activate && \
	cd src/scrape && \
	until python3 scrape_stats.py $< $@; do \
		echo "resetting vpn connection..."; \
		loc=`expresso locations | grep -- '- USA - ' | sed 's/^.*(//;s/)$$//' | shuf -n 1` && \
		expresso connect --change $$loc; \
	done

$(DATA_FINAL)/stats.csv: $(DATA_RAW)/stats-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python3 cleanup_stats.py $(DATA_RAW)/stats-raw.csv $@

scrape-clean: # Keep raw dump files.
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_FINAL)/stats.csv

scrape-clobber: # Delete all files from scraping process.
	rm -f $(DATA_RAW)/usernames-raw.csv
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_RAW)/stats-raw.csv
	rm -f $(DATA_FINAL)/stats.csv

.PHONY: scrape scrape-clean
.PRECIOUS: $(DATA_RAW)/usernames-raw.csv $(DATA_RAW)/stats-raw.csv

# Clustering --------------------------------------------------------------------------------------
cluster: $(DATA_FINAL)/clusters.csv ## Cluster players according to scraped stats.

$(DATA_FINAL)/clusters.csv:
	@source env/bin/activate && \
	cd src/cluster && python3 cluster_players.py $(DATA_FINAL)/stats.csv $@

cluster-clean:
	rm -f $(DATA_FINAL)/clusters.csv

.PHONY: cluster cluster-clean

# Dimensionality reduction ------------------------------------------------------------------------
dimreduce: $(DATA_TMP)/dim_reduced.pkl ## Reduce cluster dimensionality for visualization.

$(DATA_TMP)/cluster_analytics.pkl:
	@source env/bin/activate && \
	cd src/cluster && python3 process_clusters.py $(DATA_FINAL)/stats.csv $(DATA_FINAL)/clusters.csv $@

$(DATA_TMP)/dim_reduced.pkl: $(DATA_TMP)/cluster_analytics.pkl
	@source env/bin/activate && \
	cd src/cluster && python3 dim_reduce_clusters.py $< $@

dimreduce-clean:
	rm -f $(DATA_TMP)/cluster_analytics.pkl
	rm -f $(DATA_TMP)/dim_reduced.pkl

.PHONY: dimreduce dimreduce-clean

# Application -------------------------------------------------------------------------------------
app: $(DATA_FINAL)/app_data.pkl app-db ## Build data file and database for visualization app.

$(DATA_FINAL)/app_data.pkl: $(DATA_TMP)/cluster_analytics.pkl $(DATA_TMP)/dim_reduced.pkl
	@source env/bin/activate && \
	cd src/app && python3 build_app_data.py $^ $@

app-db: $(DATA_FINAL)/clusters.csv $(DATA_FINAL)/stats.csv
	@source env/bin/activate && \
	cd src/app && python3 build_database.py $^

app-run:
	@source env/bin/activate && python3 app

app-clean:
	rm -f $(DATA_FINAL)/app_data.pkl

.PHONY: app app-db app-run app-clean

# Upload/download ---------------------------------------------------------------------------------

upload-appdata: $(DATA_FINAL)/app_data.pkl
	aws s3 cp $< s3://$(S3_BUCKET)/$(OSRS_APPDATA_S3KEY)

upload-dataset: $(DATA_FINAL)/stats.csv $(DATA_FINAL)/clusters.csv
	aws s3 cp $(word 2,$^) s3://$(S3_BUCKET)/dataset/player-clusters.csv
	aws s3 cp $< s3://$(S3_BUCKET)/dataset/player-stats.csv
	gdrive upload --parent $(GDRIVE_DIR) --name player-clusters.csv data/processed/clusters.csv
	gdrive upload --parent $(GDRIVE_DIR) --name player-stats.csv data/processed/stats.csv

download: ## Download processed dataset from S3.
	@source env/bin/activate && \
	[ -f $(DATA_FINAL)/clusters.csv ] || python -c "from src import download_from_s3; \
	download_from_s3('$(S3_BUCKET)', 'dataset/player-clusters.csv', '$(DATA_FINAL)/clusters.csv'); \
	print()" && \
	[ -f $(DATA_FINAL)/stats.csv ] || python -c "from src import download_from_s3; \
	download_from_s3('$(S3_BUCKET)', 'dataset/player-stats.csv', '$(DATA_FINAL)/stats.csv'); \
	print()"

.PHONY: upload-appdata upload-dataset download

# Other -------------------------------------------------------------------------------------------
vim-binding:
	@source env/bin/activate && \
	jupyter contrib nbextensions install && \
	cd $(shell jupyter --data-dir)/nbextensions && \
	git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding || \
	cd vim_binding && git pull

nbextensions: vim-binding
	jupyter nbextension enable vim_binding/vim_binding
	jupyter nbextension enable rubberband/main
	jupyter nbextension enable toggle_all_line_numbers/main
	jupyter nbextension enable varInspector/main

notebook: nbextensions ## Start a local jupyter notebook server.
	@source env/bin/activate && \
	cd notebooks && jupyter notebook

lint: ## Run code style checker.
	@source env/bin/activate && \
	pycodestyle app src --ignore=E501,E302 && \
	echo "ok"

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: vim-binding nbextensions notebook lint help
