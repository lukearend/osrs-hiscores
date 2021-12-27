export SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

DATA_RAW:=$(ROOT_DIR)/data/raw
DATA_TMP:=$(ROOT_DIR)/data/interim
DATA_FINAL:=$(ROOT_DIR)/data/processed
APP_DIR:=$(ROOT_DIR)/app
DB_DIR:=$(ROOT_DIR)/volume
DB_PORT:=27017

.PHONY: all clean
all: lint analytics app run
clean: env-clean analytics-clean app-clean

##
##  Setup
.PHONY: init env-clean

init:               ## Initialize repository.
init: db-pull env extensions lint

env:                ## Build virtual environment.
	@echo "building virtual environment..."
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info && \
	source env/bin/activate
	@echo

env-clean:          ## Remove virtual environment.
	@rm -rf env

##
##  Data scraping
.PHONY: scrape scrape-clean scrape-clobber

scrape:             ## Run full data scraping process.
scrape: $(DATA_FINAL)/stats.csv
	@source env/bin/activate && \
	cd src/scrape && python3 scrape_usernames.py $<

$(DATA_RAW)/usernames-raw.csv:
	@source env/bin/activate && \
	cd src/scrape && python3 scrape_usernames.py $@ && \
	touch $@

$(DATA_TMP)/usernames.csv: $(DATA_RAW)/usernames-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python3 cleanup_usernames.py $< $@

$(DATA_RAW)/stats-raw.csv: $(DATA_TMP)/usernames.csv
	@source env/bin/activate && \
	cd src/scrape && python3 scrape_stats.py $< $@ && \
	touch $@

$(DATA_FINAL)/stats.csv: $(DATA_RAW)/stats-raw.csv
	@source env/bin/activate && \
	cd src/data && python3 cleanup_stats.py $< $@

scrape-clean:       ## Remove scraped data (but not raw files).
	touch $(DATA_RAW)/usernames-raw.csv ; \
	touch $(DATA_RAW)/stats-raw.csv ; \
	rm -f $(DATA_TMP)/usernames.csv && \
	rm -f $(DATA_FINAL)/stats.csv

scrape-clobber:     ## Remove ALL scraped data.
	rm -f $(DATA_RAW)/usernames-raw.csv
	rm -f $(DATA_RAW)/stats-raw.csv
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_FINAL)/stats.csv

##
##  Data analytics
.PHONY: analytics analytics-clean

analytics:          ## Run full processing pipeline on scraped data.
analytics: $(DATA_TMP)/clusters.pkl $(DATA_TMP)/percentiles.pkl $(DATA_TMP)/dimreduced.pkl

$(DATA_TMP)/stats.pkl: $(DATA_FINAL)/stats.csv
	@source env/bin/activate && \
	cd src/data && python3 write_stats_pkl.py $< $@

$(DATA_TMP)/clusters.pkl: $(DATA_RAW)/clusters-raw.pkl
	@source env/bin/activate && \
	cd src/data && python3 process_cluster_data.py $< $@

$(DATA_TMP)/percentiles.pkl: $(DATA_TMP)/stats.pkl $(DATA_TMP)/clusters.pkl
	@source env/bin/activate && \
	cd src/features && python3 compute_percentiles.py $^ $@

$(DATA_TMP)/dimreduced.pkl: $(DATA_TMP)/clusters.pkl $(DATA_TMP)/percentiles.pkl
	@source env/bin/activate && \
	cd src/models && python3 dim_reduce_centroids.py $^ $@

analytics-clean:    ## Remove all analytics generated from scraped data.
	rm -f $(DATA_TMP)/stats.pkl
	rm -f $(DATA_TMP)/clusters.pkl
	rm -f $(DATA_TMP)/centroids.pkl
	rm -f $(DATA_TMP)/dimreduced.pkl


##
##  Main application
.PHONY: run app app-data app-db app-clean

run:                ## Run main application.
run: db-start
	@source env/bin/activate && python3 app $(DB_PORT)

app:                ## Build application data file and database.
app: app-data db-start app-db

app-data: $(DATA_FINAL)/appdata.pkl
	@echo "installing app data"
	cp $< $(APP_DIR)/assets/appdata.pkl
	@echo

app-db: $(DATA_TMP)/stats.pkl $(DATA_TMP)/clusters.pkl
	@source env/bin/activate && \
	cd src/visuals && python3 build_database.py $^ $(DB_PORT)

$(DATA_FINAL)/appdata.pkl: $(DATA_TMP)/dimreduced.pkl $(DATA_TMP)/clusters.pkl \
                           $(DATA_TMP)/percentiles.pkl
	@source env/bin/activate && \
	cd src/visuals && python3 build_appdata.py $^ $@

app-clean:          ## Remove application data and database.
app-clean: db-stop
	rm -f $(DATA_FINAL)/appdata.pkl
	rm -f $(APP_DIR)/assets/appdata.pkl
	rm -rf $(DB_DIR)

##
##  Database
.PHONY: db-pull db-start db-stop

db-pull:            ## Pull latest version of MongoDB.
	@echo "pulling mongodb..."
	@docker pull mongo
	@echo

db-start:           ## Start database service.
	@echo "starting database..."
	@mkdir -p $(DB_DIR) && \
	docker stop osrs-hiscores > /dev/null 2>&1 ; \
	docker run --rm -d --name osrs-hiscores \
	-v $(DB_DIR):/data/db \
	-p $(DB_PORT):$(DB_PORT) mongo
	@echo -n "warming up... " && sleep 1
	@echo "done" && echo

db-stop:            ## Stop database service.
	@echo "stopping database..."
	@docker stop osrs-hiscores 2> /dev/null
	@echo

##
##  Other
.PHONY: vim-binding nbextensions notebook lint help

vim-binding:
	@source env/bin/activate && \
	jupyter contrib nbextensions install && \
	cd $(shell jupyter --data-dir)/nbextensions && \
	git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding || \
	cd vim_binding && git pull

nbextensions: vim-binding
	jupyter nbextension enable vim_binding/vim_binding && \
	jupyter nbextension enable rubberband/main && \
	jupyter nbextension enable toggle_all_line_numbers/main && \
	jupyter nbextension enable varInspector/main

notebook:           ## Start a local jupyter notebook server.
notebook: nbextensions
	@source env/bin/activate && \
	cd notebooks && jupyter notebook

lint:               ## Run code style checker.
	@source env/bin/activate && \
	pycodestyle app src --ignore=E501 && \
	echo "ok"

help:               ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

##
