export SHELL := /bin/bash
export PYTHONPATH := $(shell pwd)

all: init

init: 				## Initialize repository.
init: clean-env env nbextensions lint db-pull

env: 				## Build virtual environment.
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info && \
	source env/bin/activate

clean-env: 			## Remove virtual environment.
	@rm -rf env

scrape: data/processed/stats.csv

clean-scrape:       		## Remove all scraped data (WARNING: be sure you want to do this).
	rm -f data/raw/usernames-raw.csv
	rm -f data/interim/usernames.csv
	rm -f data/raw/stats-raw.csv

data/raw/usernames-raw.csv:
	@source env/bin/activate && \
	cd hiscores/data && python3 scrape_usernames.py

data/interim/usernames.csv: data/raw/usernames-raw.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 cleanup_usernames.py

data/raw/stats-raw.csv: data/interim/usernames.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 scrape_stats.py

data/processed/stats.csv: data/raw/stats-raw.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 cleanup_stats.py

analytics: data/processed/clusters.csv data/processed/stats.pkl data/processed/clusters.pkl \
           data/processed/centroids.pkl data/processed/dimreduced.pkl

clean-analytics:		## Remove all analytic results computed from scraped data.
	rm -f data/processed/stats.pkl
	rm -f data/processed/clusters.pkl
	rm -f data/processed/players.pkl
	rm -f data/processed/centroids.pkl
	rm -f data/processed/dimreduced.pkl

data/processed/clusters.pkl: data/raw/clusters-raw.pkl
	@source env/bin/activate && \
	cd hiscores/data && python3 process_cluster_data.py

data/processed/stats.pkl: data/processed/stats.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 write_stats_pkl.py

data/processed/players.pkl: data/processed/stats.pkl data/processed/clusters.pkl
	@source env/bin/activate && \
	cd hiscores/data && python3 write_players_pkl.py

data/processed/centroids.pkl: data/processed/stats.pkl data/processed/clusters.pkl
	@source env/bin/activate && \
	cd hiscores/features && python3 compute_cluster_centroids.py

data/processed/dimreduced.pkl: data/processed/clusters.pkl data/processed/centroids.pkl
	@source env/bin/activate && \
	cd hiscores/models && python3 dim_reduce_centroids.py

db: db-pull db-start db-build

clean-db: 
	docker stop osrs-hiscores ; \
	docker rm osrs-hiscores ; \
	rm -rf $(shell pwd)/db/volume/*

db-pull:
	docker pull mongo

db-start:
	docker stop osrs-hiscores ; \
	docker run --rm --name osrs-hiscores -v $(shell pwd)/db/volume:/data/db -d mongo

db-build:
	@source env/bin/activate && \
	cd db && python3 build_database.py

app:				## Run visualization app.
	@source env/bin/activate && python3 app.py

all: init analytics db app

nbextensions:			## Install jupyter notebook extensions.
	@source env/bin/activate && \
	jupyter contrib nbextensions install && \
	cd $(shell jupyter --data-dir)/nbextensions && \
	rm -rf vim_binding && \
	git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding && \
	jupyter nbextension enable vim_binding/vim_binding && \
	jupyter nbextension enable rubberband/main && \
	jupyter nbextension enable toggle_all_line_numbers/main && \
	jupyter nbextension enable varInspector/main

notebook:			## Start a local jupyter notebook server.
	@source env/bin/activate && \
	cd notebooks && \
	jupyter notebook

lint: 				## Run code style checker.
	@source env/bin/activate && \
	pycodestyle hiscores --ignore=E501 && \
	echo "ok"

help: 				## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

.PHONY: all analytics app clean-analytics clean-env clean-scrape
.PHONY: env help init lint nbextensions notebook scrape
