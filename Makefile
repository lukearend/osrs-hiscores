export SHELL := /bin/bash
export PYTHONPATH := $(shell pwd)

all: init build-data

build-data:			## Download and build hiscores dataset.
build-data: data/processed/stats.csv data/processed/stats.pkl

clean-data:         ## Remove downloaded data.
	@rm data/external/* && \
	rm data/interim/* && \
	rm data/processed/* && \
	rm data/raw/*

clean-env: 			## Remove virtual environment.
	@rm -rf env

env: 				## Build virtual environment.
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info && \
	source env/bin/activate

help: 				## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

init: 				## Initialize repository.
init: clean-env env nbextensions lint

data/raw/stats-raw.csv: data/interim/usernames.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 scrape_stats.py

data/processed/stats.csv: data/raw/stats-raw.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 cleanup_stats.py

data/raw/usernames-raw.csv:
	@source env/bin/activate && \
	cd hiscores/data && python3 scrape_usernames.py

data/interim/usernames.csv: data/raw/usernames-raw.csv
	@source env/bin/activate && \
	cd hiscores/data && python3 cleanup_usernames.py

lint: 				## Run code style checker.
	@source env/bin/activate && \
	pycodestyle hiscores --ignore=E501 && \
	echo "ok"

nbextensions:		## Install jupyter notebook extensions.
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

.PHONY: all clean-data clean-env help init lint nbextensions notebook
