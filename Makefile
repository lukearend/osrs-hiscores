export SHELL := /bin/bash
export PYTHONPATH := $(shell pwd)

all: init build-data

build-data:	## Download and build hiscores dataset.
build-data: data/processed/stats.csv

clean: 		## Delete all data and packages.
	rm -rf env &&
	rm -rf data/raw/* &&
	rm -rf data/interim/* &&
	rm -rf data/processed/*

env: 		## Build virtual environment.
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	source env/bin/activate

help: 		## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

init: 		## Initialize repository.
init: env jupyter lint

data/raw/stats-raw.csv: data/raw/usernames.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 scrape_stats.py

data/processed/stats.csv: data/raw/stats-raw.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 cleanup_stats.py

data/raw/usernames-raw.csv: env
	@source env/bin/activate && \
	cd hiscores/data && python3 scrape_usernames.py

data/raw/usernames.csv: data/raw/usernames-raw.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 cleanup_usernames.py

jupyter:
	mkdir -p $(shell jupyter --data-dir)/nbextensions
	pushd $(shell jupyter --data-dir)/nbextensions && \
	rm -rf vim_binding && \
	git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding && \
	popd
	jupyter nbextension enable vim_binding/vim_binding
	jupyter nbextension enable rubberband/main
	jupyter nbextension enable toggle_all_line_numbers/main
	jupyter nbextension enable varInspector/main

lint: 		## Run code style checker.
	@source env/bin/activate && \
	pycodestyle hiscores --ignore=E501 && \
	echo "ok"

# Note: remove data/raw/stats-raw.csv from .PHONY when it is complete
.PHONY: data/raw/stats-raw.csv
.PHONY: all build-data clean help init jupyter lint
