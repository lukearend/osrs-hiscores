export SHELL:=/bin/bash
export AMBER_LICENSE_ID:=luke-dev

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
DATA_RAW:=$(ROOT_DIR)/data/raw
DATA_TMP:=$(ROOT_DIR)/data/interim
DATA_FINAL:=$(ROOT_DIR)/data/processed
APP_DIR:=$(ROOT_DIR)/app
DB_DIR:=$(ROOT_DIR)/volume
DB_PORT:=27017

.DEFAULT_GOAL := help

all: lint init scrape cluster app
clean: env-clean data-clean results-clean 

# Setup -------------------------------------------------------------------------------------------
init: db-pull env extensions ## Setup project dependencies.

env:
	@echo "building virtual environment..."
	@python3 -m venv env && \
	source env/bin/activate && \
	pip3 install --upgrade pip && \
	pip3 install -r requirements.txt && \
	rm -rf *.egg-info && \
	source env/bin/activate
	@echo

env-clean:
	@rm -rf env

.PHONY: all clean init env-clean

# Data scraping -----------------------------------------------------------------------------------
scrape: $(DATA_FINAL)/stats.csv ## Run data scrape of OSRS hiscores.

scrape-clean:
	@[ -f $(DATA_RAW)/usernames-raw.csv ] && touch $(DATA_RAW)/usernames-raw.csv; \
	[ -f $(DATA_RAW)/stats-raw.csv ] &&  touch $(DATA_RAW)/stats-raw.csv ; \
	rm -f $(DATA_TMP)/usernames.csv && \
	rm -f $(DATA_FINAL)/stats.csv &&

$(DATA_RAW)/usernames-raw.csv:
	@source env/bin/activate && \
	cd src/data && \
	until python3 scrape_usernames.py $@ ; do \
		echo "resetting vpn connection..." ; \
		loc=`expresso locations | grep -- '- USA - ' | sed 's/^.*(//;s/)$$//' | shuf -n 1` && \
		expresso connect --change $$loc ; \
	done
	@echo

$(DATA_TMP)/usernames.csv: $(DATA_RAW)/usernames-raw.csv
	@source env/bin/activate && \
	cd src/data && python3 cleanup_usernames.py $< $@
	@echo

$(DATA_RAW)/stats-raw.csv: $(DATA_TMP)/usernames.csv
	@source env/bin/activate && \
	cd src/data && \
	until python3 scrape_stats.py $< $@; do \
		echo "resetting vpn connection..."; \
		loc=`expresso locations | grep -- '- USA - ' | sed 's/^.*(//;s/)$$//' | shuf -n 1` && \
		expresso connect --change $$loc; \
	done
	@echo

$(DATA_FINAL)/stats.csv: $(DATA_RAW)/stats-raw.csv
	@source env/bin/activate && \
	cd src/data && python3 cleanup_stats.py $(DATA_RAW)/stats-raw.csv $@
	@echo

.PHONY: scrape scrape-clean
.PRECIOUS: $(DATA_RAW)/usernames-raw.csv $(DATA_RAW)/stats-raw.csv

# Clustering --------------------------------------------------------------------------------------
cluster: $(DATA_FINAL)/clusters.csv ## Cluster players according to scraped stats.

cluster-clean:
	@[ -f $(DATA_FINAL)/clusters.csv ] && touch $(DATA_FINAL)/clusters.csv

$(DATA_FINAL)/clusters.csv: $(DATA_FINAL)/stats.csv
	@source env/bin/activate && \
	cd src/models && python3 cluster_players.py $< $@
	@echo

.PHONY: cluster cluster-clean
.PRECIOUS: $(DATA_FINAL)/clusters.csv

# Dimensionality reduction ------------------------------------------------------------------------
dimreduce: $(DATA_TMP)/dim_reduced.pkl ## Reduce cluster dimensionality for visualization.

dimreduce-clean:
	rm -f $(DATA_TMP)/cluster_analytics.pkl && \
	rm -f $(DATA_TMP)/dim_reduced.pkl

$(DATA_TMP)/cluster_analytics.pkl: $(DATA_FINAL)/stats.csv $(DATA_FINAL)/clusters.csv
	@source env/bin/activate && \
	cd src/features && python3 process_clusters.py $^ $@
	@echo

$(DATA_TMP)/dim_reduced.pkl: $(DATA_TMP)/cluster_analytics.pkl
	@source env/bin/activate && \
	cd src/models && python3 dim_reduce_clusters.py $< $@
	@echo

.PHONY: dimreduce dimreduce-clean

# Visualization -----------------------------------------------------------------------------------
app: $(APP_DIR)/assets/app_data.pkl db ## Build application data/database.

app-clean: db-stop
	rm -f $(DATA_FINAL)/appdata.pkl
	rm -f $(APP_DIR)/assets/appdata.pkl
	rm -rf $(DB_DIR)

app-run: db-start ## Run main application for visualizing results.
	@source env/bin/activate && python3 app $(DB_PORT)

$(APP_DIR)/assets/app_data.pkl: $(DATA_TMP)/cluster_analytics.pkl $(DATA_TMP)/dim_reduced.pkl
	@source env/bin/activate && \
	cd src/data && python3 build_appdata.py $^ $@
	@echo

.PHONY: app app-clean app-run

# Database ----------------------------------------------------------------------------------------
db: $(DATA_FINAL)/clusters.csv db-pull db-start ## Build application database.
	@source env/bin/activate && \
	cd src/data && python3 build_database.py $^ $(DB_PORT)
	@echo

db-pull: ## Pull latest version of MongoDB.
	@docker pull mongo

db-start: ## Start database container.
	@mkdir -p $(DB_DIR) && \
	docker stop osrs-hiscores-db > /dev/null 2>&1 ; \
	docker run --rm -d --name osrs-hiscores-db \
	-v $(DB_DIR):/data/db -p $(DB_PORT):$(DB_PORT) mongo
	@echo -n "starting... " && sleep 2 && echo -e "done\n"

db-stop: ## Stop database container.
	@docker stop osrs-hiscores-db 2> /dev/null

.PHONY: db db-pull db-start db-stop

# Other -------------------------------------------------------------------------------------------
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

notebook: nbextensions ## Start a local jupyter notebook server.
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
