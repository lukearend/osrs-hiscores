export SHELL := /bin/bash
export PYTHONPATH := $(shell pwd)

all: init

# Givens:
# data/raw/clusters.pkl
# data/processed/clusters.csv
# data/processed/stats.csv

init: 				## Initialize repository.
init: clean-env env nbextensions lint

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

clean-scrape:       		## Removes all scraped data (WARNING: be sure you want to do this).
	rm data/raw/usernames-raw.csv
	rm data/interim/usernames.csv
	rm data/raw/stats-raw.csv

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

analytics: data/processed/dimreduced.pkl

clean-analytics:		## Removes all analytic results computed from scraped data.
	rm data/processed/stats.pkl
	rm data/processed/clusters.csv
	rm data/processed/clusters.pkl
	rm data/processed/centroids.pkl
	rm data/processed/dimreduced.pkl

data/processed/stats.pkl: data/processed/stats.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 write_stats_pkl.py

data/processed/clusters.csv: data/raw/clusters.pkl data/processed/stats.pkl
	@source env/bin/activate && \
	cd hiscores/data && python3 write_cluster_csv.py

data/processed/clusters.pkl: data/raw/clusters.pkl
	@source env/bin/activate && \
	cd hiscores/data && python3 process_cluster_data.py

# TODO: fix this so that centroid data includes total level as first column
data/processed/centroids.pkl: data/processed/clusters.pkl data/processed/stats.pkl
	@source env/bin/activate && \
	cd hiscores/features && python3 compute_cluster_centroids.py

# TODO: fix this so that it excludes total level column (once that's been added)
# TODO: change generate-scatterplots -> 2.1-umap-params
# TODO: write generate-scatterplots notebook, plot and save 3 dim reductions.
data/processed/dimreduced.pkl: data/processed/clusters.pkl data/processed/centroids.pkl
	@source env/bin/activate && \
	cd hiscores/models && python3 dim_reduce_centroids.py

# TODO: continue with this once total level column has been added
# TODO: smaller marker sizes, tooltip lookup of centroids
app:				## Run visualization app.
app: data/processed/dimreduced.pkl
	@source env/bin/activate && \
	cd hiscores/visualization && python3 app.py

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
