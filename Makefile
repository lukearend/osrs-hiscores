export SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

DATA_RAW:=$(ROOT_DIR)/data/raw
DATA_TMP:=$(ROOT_DIR)/data/interim
DATA_FINAL:=$(ROOT_DIR)/data/processed
APP_DIR:=$(ROOT_DIR)/app
DB_DIR:=$(ROOT_DIR)/volume
DB_PORT:=27017

.DEFAULT_GOAL := help
all: init analytics app run

# Setup
init: db-pull env extensions lint ## Setup project dependencies.

env: ## Build project virtual environment.
	@echo "building virtual environment..."
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info && \
	source env/bin/activate
	@echo

env-clean: ## Remove project virtual environment.
	@rm -rf env

clean: env-clean scrape-clean analytics-clean app-clean

.PHONY: all init env-clean clean

# Data scraping
scrape: $(DATA_FINAL)/stats.csv ## Run data scraping process.

$(DATA_RAW)/usernames-raw.csv:
	@source env/bin/activate && \
	cd src/scrape && \
	until python3 scrape_usernames.py $@ ; do                                                   \
		echo "resetting vpn connection..." ;                                                    \
		loc=`expresso locations | grep -- '- USA - ' | sed 's/^.*(//;s/)$$//' | shuf -n 1` &&   \
		expresso connect --change $$loc ;                                                       \
	done
	@echo

$(DATA_TMP)/usernames.csv: $(DATA_RAW)/usernames-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python3 cleanup_usernames.py $< $@
	@echo

$(DATA_RAW)/stats-raw.csv: $(DATA_TMP)/usernames.csv
	@source env/bin/activate && \
	cd src/scrape && \
	until python3 scrape_stats.py $< $@; do                                                     \
		echo "resetting vpn connection..." ;                                                    \
		loc=`expresso locations | grep -- '- USA - ' | sed 's/^.*(//;s/)$$//' | shuf -n 1` &&   \
		expresso connect --change $$loc ;                                                       \
	done
	@echo

$(DATA_FINAL)/stats.csv: $(DATA_RAW)/stats-raw.csv
	@source env/bin/activate && \
	cd src/scrape && python3 cleanup_stats.py $< $@
	@echo

scrape-clean: ## Remove processed scraped data, but not raw files.
	touch $(DATA_RAW)/usernames-raw.csv ; \
	touch $(DATA_RAW)/stats-raw.csv ; \
	rm -f $(DATA_TMP)/usernames.csv && \
	rm -f $(DATA_FINAL)/stats.csv

scrape-clobber: ## Remove ALL scraped data.
	rm -f $(DATA_RAW)/usernames-raw.csv
	rm -f $(DATA_RAW)/stats-raw.csv
	rm -f $(DATA_TMP)/usernames.csv
	rm -f $(DATA_FINAL)/stats.csv

.PHONY: scrape scrape-clean scrape-clobber
.PHONY: $(DATA_RAW)/usernames-raw.csv $(DATA_RAW)/stats-raw.csv
.PRECIOUS: $(DATA_RAW)/usernames-raw.csv $(DATA_RAW)/stats-raw.csv

# Data analytics
analytics: ## Run analytics pipeline on scraped data.
analytics: $(DATA_TMP)/clusters.pkl $(DATA_TMP)/percentiles.pkl $(DATA_TMP)/dimreduced.pkl

$(DATA_TMP)/stats.pkl: $(DATA_FINAL)/stats.csv
	@source env/bin/activate && \
	cd src/data && python3 write_stats_pkl.py $< $@
	@echo

$(DATA_TMP)/clusters.pkl: $(DATA_RAW)/clusters-raw.pkl
	@source env/bin/activate && \
	cd src/data && python3 augment_cluster_data.py $< $@
	@echo

$(DATA_TMP)/percentiles.pkl: $(DATA_TMP)/stats.pkl $(DATA_TMP)/clusters.pkl
	@source env/bin/activate && \
	cd src/features && python3 compute_percentiles.py $^ $@
	@echo

$(DATA_TMP)/dimreduced.pkl: $(DATA_TMP)/clusters.pkl $(DATA_TMP)/percentiles.pkl
	@source env/bin/activate && \
	cd src/models && python3 dim_reduce_centroids.py $^ $@
	@echo

analytics-clean: ## Remove all analytics generated from scraped data.
	rm -f $(DATA_TMP)/stats.pkl
	rm -f $(DATA_TMP)/clusters.pkl
	rm -f $(DATA_TMP)/centroids.pkl
	rm -f $(DATA_TMP)/dimreduced.pkl

.PHONY: analytics analytics-clean

# Main application
run: ## Run application for visualizing results.
	@source env/bin/activate && python3 app $(DB_PORT)

app: app-data db-start app-db ## Build application dependencies.

app-data: $(DATA_FINAL)/appdata.pkl ## Build application data file.
	@cp $< $(APP_DIR)/assets/appdata.pkl

app-db: $(DATA_TMP)/stats.pkl $(DATA_TMP)/clusters.pkl ## Build application database.
	@source env/bin/activate && \
	cd src/visuals && python3 build_database.py $^ $(DB_PORT)
	@echo

$(DATA_FINAL)/appdata.pkl: $(DATA_TMP)/dimreduced.pkl $(DATA_TMP)/clusters.pkl \
                           $(DATA_TMP)/percentiles.pkl
	@source env/bin/activate && \
	cd src/visuals && python3 build_appdata.py $^ $@
	@echo

app-clean: db-stop ## Remove application data and database.
	rm -f $(DATA_FINAL)/appdata.pkl
	rm -f $(APP_DIR)/assets/appdata.pkl
	rm -rf $(DB_DIR)

.PHONY: run app app-data app-db app-clean

# Database
db-pull: ## Pull latest version of MongoDB.
	@docker pull mongo

db-start: ## Start database container.
	@mkdir -p $(DB_DIR) && \
	docker stop osrs-hiscores > /dev/null 2>&1 ; \
	docker run --rm -d --name osrs-hiscores \
	-v $(DB_DIR):/data/db \
	-p $(DB_PORT):$(DB_PORT) mongo
	@echo -n "starting... " && sleep 2 && echo -e "done\n"

db-stop: ## Stop database container.
	@docker stop osrs-hiscores 2> /dev/null
	@echo

.PHONY: db-pull db-start db-stop

# Other
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

notebook: ## Start a local jupyter notebook server.
notebook: nbextensions
	@source env/bin/activate && \
	cd notebooks && jupyter notebook

lint: ## Run code style checker.
	@source env/bin/activate && \
	pycodestyle app src --ignore=E501 && \
	echo "ok"

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: vim-binding nbextensions notebook lint help
