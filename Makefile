export SHELL := /bin/bash
export PYTHONPATH := $(shell pwd)

all: init build-data

activate: env		## Activate virtual environment.


build-data:			## Download and build hiscores dataset.
build-data: data/processed/stats.csv

clean: 				## Remove virtual environment.
	rm -rf env

env: 				## Build virtual environment.
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	source env/bin/activate

help: 				## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

init: 				## Initialize repository.
init: clean env nbextensions lint

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

lint: 				## Run code style checker.
	@source env/bin/activate && \
	pycodestyle hiscores --ignore=E501 && \
	echo "ok"

nbextensions: env	## Install jupyter notebook extensions.
	mkdir -p $(shell jupyter --data-dir)/nbextensions
	pushd $(shell jupyter --data-dir)/nbextensions && \
	rm -rf vim_binding && \
	git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding && \
	popd
	jupyter nbextension enable vim_binding/vim_binding
	jupyter nbextension enable rubberband/main
	jupyter nbextension enable toggle_all_line_numbers/main
	jupyter nbextension enable varInspector/main

# Note: remove data/raw/stats-raw.csv from .PHONY when it is complete
.PHONY: data/raw/stats-raw.csv
.PHONY: all build-data clean help init lint nbextensions
