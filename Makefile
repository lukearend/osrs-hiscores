export SHELL := /bin/bash

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
DATA_RAW:=$(ROOT_DIR)/data/raw
DATA_TMP:=$(ROOT_DIR)/data/interim
DATA_FINAL:=$(ROOT_DIR)/data/processed


.PHONY: all
all: init analytics db run


.PHONY: init env clean-env
init:               ## Initialize repository.
init: clean-env env nbextensions lint db-pull

env:                ## Build virtual environment.
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info && \
	source env/bin/activate

clean-env:          ## Remove virtual environment.
	@rm -rf env


.PHONY: scrape clean-scrape
scrape:             ## Run full data scraping process.
scrape: $(DATA_FINAL)/stats.csv

$(DATA_RAW)/usernames-raw.csv:
	@source env/bin/activate && \
	cd src/data && python3 scrape_usernames.py $(DATA_RAW)/usernames-raw.csv

$(DATA_TMP)/usernames.csv: $(DATA_RAW)/usernames-raw.csv
	@source env/bin/activate && \
	cd src/data && python3 cleanup_usernames.py $< $@

$(DATA_RAW)/stats-raw.csv: $(DATA_TMP)/usernames.csv
	@source env/bin/activate && \
	cd src/data && python3 scrape_stats.py $< $(DATA_RAW)/stats-raw.csv

$(DATA_FINAL)/stats.csv: $(DATA_RAW)/stats-raw.csv
	@source env/bin/activate && \
	cd src/data && python3 cleanup_stats.py $< $@

clean-scrape:       ## Remove scraped data (be sure you want to do this).
	rm -f $(DATA_RAW)/usernames-raw.csv
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_RAW)/stats-raw.csv


.PHONY: analytics clean-analytics
analytics:          ## Run full processing pipeline on scraped data.
analytics: $(DATA_FINAL)/appdata.pkl

$(DATA_FINAL)/stats.pkl: $(DATA_FINAL)/stats.csv
	@source env/bin/activate && \
	cd src/data && python3 write_stats_pkl.py $< $@

$(DATA_FINAL)/clusters.pkl: $(DATA_RAW)/clusters-raw.pkl
	@source env/bin/activate && \
	cd src/data && python3 process_cluster_data.py $< $@

$(DATA_FINAL)/percentiles.pkl: $(DATA_FINAL)/stats.pkl $(DATA_FINAL)/clusters.pkl
	@source env/bin/activate && \
	cd src/features && python3 compute_percentiles.py $^ $@

$(DATA_FINAL)/dimreduced.pkl: $(DATA_FINAL)/clusters.pkl $(DATA_FINAL)/percentiles.pkl
	@source env/bin/activate && \
	cd src/models && python3 dim_reduce_centroids.py $^ $@

$(DATA_FINAL)/appdata.pkl: $(DATA_FINAL)/dimreduced.pkl $(DATA_FINAL)/clusters.pkl \
                           $(DATA_FINAL)/percentiles.pkl
	@source env/bin/activate && \
	cd src/visuals && python3 build_appdata.py $^ $@

clean-analytics:    ## Remove all analytic results computed from scraped data.
	rm -f $(DATA_FINAL)/stats.pkl
	rm -f $(DATA_FINAL)/clusters.pkl
	rm -f $(DATA_FINAL)/centroids.pkl
	rm -f $(DATA_FINAL)/dimreduced.pkl
	rm -f $(DATA_FINAL)/appdata.pkl


.PHONY: db db-pull db-start db-build db-stop clean-db
db:                 ## Populate application database with player/cluster results.
db: db-pull db-start db-build

db-pull:
	docker pull mongo

db-start:
	mkdir -p volume && \
	docker stop osrs-hiscores > /dev/null 2>&1 ; \
	docker run --rm -d --name osrs-hiscores \
	-v $(ROOT_DIR)/volume:/data/db \
	-p 27017:27017 mongo

db-build: $(DATA_FINAL)/stats.pkl $(DATA_FINAL)/clusters.pkl
	@source env/bin/activate && \
	cd src/visuals && python3 build_database.py $^ $@

db-stop:
	docker stop osrs-hiscores > /dev/null 2>&1

clean-db:           ## Wipe away application database.
clean-db: db-stop
	docker rm osrs-hiscores > /dev/null 2>&1
	rm -rf volume


.PHONY: run
run:                ## Run main application.
	@source env/bin/activate && python3 app $(DATA_FINAL)/appdata.pkl


.PHONY: nbextensions notebook lint help
nbextensions:       ## Install jupyter notebook extensions.
	@source env/bin/activate && \
	jupyter contrib nbextensions install && \
	cd $(shell jupyter --data-dir)/nbextensions && \
	rm -rf vim_binding && \
	git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding && \
	jupyter nbextension enable vim_binding/vim_binding && \
	jupyter nbextension enable rubberband/main && \
	jupyter nbextension enable toggle_all_line_numbers/main && \
	jupyter nbextension enable varInspector/main

notebook:           ## Start a local jupyter notebook server.
	@source env/bin/activate && \
	cd notebooks && \
	jupyter notebook

lint:               ## Run code style checker.
	@source env/bin/activate && \
	pycodestyle app src --ignore=E501 && \
	echo "ok"

help:               ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
