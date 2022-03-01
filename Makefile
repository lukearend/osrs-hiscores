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

all: init scrape cluster dimreduce app # Scrape data, process it and build final application.
build: init download test dimreduce app # Build final application from downloaded pre-scraped data.
clean: env-clean scrape-clean cluster-clean dimreduce-clean app-clean # Remove all generated results.
run:
	@source env/bin/activate && python3 app

.PHONY: all build clean run

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

.PHONY: init env env-clean

# Data scraping -----------------------------------------------------------------------------------
scrape: $(DATA_FINAL)/player-stats.csv ## Run data scrape of OSRS hiscores.

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

$(DATA_FINAL)/player-stats.csv: $(DATA_RAW)/stats-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python3 cleanup_stats.py $(DATA_RAW)/stats-raw.csv $@

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
	cd src/models && python3 fit_clusters.py $(DATA_FINAL)/player-stats.csv $@

$(DATA_FINAL)/player-clusters.csv: $(DATA_FINAL)/cluster-centroids.csv
	@source env/bin/activate && \
	cd src/models && python3 cluster_players.py $(DATA_FINAL)/player-stats.csv $< $@

cluster-clean:
	rm -f $(DATA_FINAL)/cluster-centroids.csv
	rm -f $(DATA_FINAL)/player-clusters.csv

.PHONY: cluster cluster-clean

# Dimensionality reduction ------------------------------------------------------------------------
dimreduce: $(DATA_TMP)/dim_reduced.pkl ## Reduce cluster dimensionality for visualization.

$(DATA_TMP)/dim_reduced.pkl:
	@source env/bin/activate && \
	cd src/models && python3 dim_reduce_clusters.py $(DATA_FINAL)/cluster-centroids.csv $@

dimreduce-clean:
	rm -f $(DATA_TMP)/clusters_xyz.pkl

.PHONY: dimreduce dimreduce-clean

# Application -------------------------------------------------------------------------------------
app: $(DATA_FINAL)/app_data.pkl app-db ## Build data file and database for visualization app.

$(DATA_TMP)/cluster_analytics.pkl:
	@source env/bin/activate && \
	cd src/results && python3 postprocess_clusters.py $(DATA_FINAL)/player-stats.csv $(DATA_FINAL)/player-clusters.csv $@

$(DATA_FINAL)/app_data.pkl: $(DATA_FINAL)/cluster-centroids.csv $(DATA_TMP)/cluster_analytics.pkl $(DATA_TMP)/clusters_xyz.pkl
	@source env/bin/activate && \
	cd src/results && python3 build_app_data.py $^ $@

app-db: $(DATA_FINAL)/player-stats.csv $(DATA_FINAL)/player-clusters.csv
	@source env/bin/activate && \
	cd src/results && python3 build_database.py $^

app-clean:
	rm -f $(DATA_FINAL)/app_data.pkl

.PHONY: app app-db app-clean

# Upload/download ---------------------------------------------------------------------------------

upload-appdata: $(DATA_FINAL)/app_data.pkl
	aws s3 cp $< s3://$(OSRS_S3_BUCKET)/$(OSRS_APPDATA_S3KEY)

upload-dataset: $(DATA_FINAL)/player-stats.csv $(DATA_FINAL)/cluster-centroids.csv $(DATA_FINAL)/player-clusters.csv
	aws s3 cp $(word 2,$^) s3://$(OSRS_S3_BUCKET)/dataset/cluster-centroids.csv
	aws s3 cp $(word 3,$^) s3://$(OSRS_S3_BUCKET)/dataset/player-clusters.csv
	aws s3 cp $< s3://$(OSRS_S3_BUCKET)/dataset/player-stats.csv
	gdrive upload --parent $(OSRS_GDRIVE_DIR) --name cluster-centroids.csv data/processed/cluster-centroids.csv
	gdrive upload --parent $(OSRS_GDRIVE_DIR) --name player-clusters.csv data/processed/player-clusters.csv
	gdrive upload --parent $(OSRS_GDRIVE_DIR) --name player-stats.csv data/processed/player-stats.csv

download: ## Download processed dataset from S3.
	@source env/bin/activate && \
	[ -f $(DATA_FINAL)/player-clusters.csv ] || python -c "from src import download_from_s3; \
	download_from_s3('$(OSRS_S3_BUCKET)', 'dataset/player-clusters.csv', '$(DATA_FINAL)/player-clusters.csv'); \
	print()" && \
	[ -f $(DATA_FINAL)/cluster-centroids.csv ] || python -c "from src import download_from_s3; \
	download_from_s3('$(OSRS_S3_BUCKET)', 'dataset/cluster-centroids.csv', '$(DATA_FINAL)/cluster-centroids.csv'); \
	print()"
	[ -f $(DATA_FINAL)/player-stats.csv ] || python -c "from src import download_from_s3; \
	download_from_s3('$(OSRS_S3_BUCKET)', 'dataset/player-stats.csv', '$(DATA_FINAL)/player-stats.csv'); \
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
	jupyter notebook

dev-instance: ## Connect to EC2 instance for development.
	ssh -i ~/.aws/osrs-dev.pem ec2-user@$(OSRS_EC2_IP)

lint$(OSRS_EC2_IP): ## Run code style$(OSRS_EC2_IP) checker.$(OSRS_EC2_IP)$(OSRS_EC2_IP)$(OSRS_EC2_IP)$(OSRS_EC2_IP)$(OSRS_EC2_IP)$(OSRS_EC2_IP)
	@source env/bin/activate && \
	pycodestyle app src --ignore=E501,E302 && \
	echo "code check passed"

$(TEST_DIR)/data/player-stats-10000.csv: # small subsample of the full dataset for unit testing
	@source env/bin/activate && \
	cd test && python3 build_stats_10000.py $(DATA_FINAL)/player-stats.csv $<

test: lint $(TEST_DIR)/data/player-stats-10000.csv ## Run unit tests for data pipeline.
	@source env/bin/activate && \
	pytest test -sv

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: vim-binding nbextensions notebook lint test help
