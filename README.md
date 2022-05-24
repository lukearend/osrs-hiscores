osrs-hiscores
=============

A quantitative analysis of the OSRS hiscores, complete with open-source dataset and code.

This repository is accompanied by a few important data files:

1. `player-stats.csv` (163 MB): Skill levels in all 23 skills for the top 2 million OSRS accounts.
2. `cluster-centroids.csv` (1 MB): Central values for clusters that emerge from partitioning player dataset into groups based on account similarity. Each centroid is a vector of values between 1-99 in "OSRS skill" space.
3. `player-clusters.csv` (44.6 MB): Cluster IDs per player for three separate clustering runs, grouping similar accounts according to (i) all skills, (ii) combat skills only and (iii) non-combat skills only.
4. `stats-raw.csv` (1.1 GB): Rank, level, xp, clues, minigame and boss stats for the top 2 million OSRS players. This file is the raw output from the scraping process.

These files are **not included in the repo** due to file size constraints, and can be downloaded separately from the following public Google Drive folder: <https://drive.google.com/drive/folders/***REMOVED***?usp=sharing>

Player stats were scraped from the [official OSRS hiscores](https://secure.runescape.com/m=hiscore_oldschool/overall) [TODO: between 00:00 and 18:00 CST on Dec 28, 2021].

Project organization
--------------------

    ├── LICENSE
    ├── Makefile         <- Top-level Makefile for building and running project.
    ├── README.md        <- The top-level README for developers using this project.
    │
    ├── assets           <- Assets used by Dash application.           
    ├── bin              <- Utility executables.
    │
    ├── data
    │   ├── final        <- The final, canonical data set.
    │   ├── interim      <- Intermediate data that has been transformed.
    │   └── raw          <- The original, immutable data dump.
    │
    ├── ref              <- Reference files used in data processing.
    ├── scripts          <- Scripts for the stages of the data processing pipeline.
    │
    ├── src
    │   ├── app          <- Application code.
    │   ├── analysis     <- Data science and analytics.
    │   └── scrape       <- Scraping hiscores data.
    │
    ├── test             <- Unit and integration tests.
    │
    ├── app.py           <- Main script for Dash application.
    ├── Procfile         <- Entry point for deployment as a Heroku application.
    ├── requirements.txt <- Dependencies file for reproducing the project environment.
    └── setup.py         <- Setup file for installing this project through pip.

Usage
-----

At a high level, this repository implements two things:

1. The following data science pipeline:

    ```
    scrape hiscores data
             ↓
    cluster players by stats
             ↓
    project clusters to 3D
             ↓
    build application data
    ```

2. A [Dash](https://plotly.com/dash/) application for visualizing the results.

The stages of the data pipeline are driven by a [Makefile](https://opensource.com/article/18/8/what-how-makefile) with top-level `make` targets for each data processing stage:

1. `make init`: set up project environment and install dependencies.
2. `make scrape`: scrape data from the official OSRS hiscores. The scraping process takes about 12 hours.
3. `make clean`: transform raw output from the scraping process into a cleaned data set.
4. `make cluster`: cluster players into groups of similar accounts according to their stats. The clustering algorithm used is [k-means](https://en.wikipedia.org/wiki/K-means_clustering), implemented by the [faiss](https://github.com/facebookresearch/faiss) library. Running the clustering process for 2 million players and 2000 clusters takes about 2.5 hours on a 2021 M1 Macbook Pro.
5. `make dimreduce`: map cluster centroids from high-dimensional space to 3D for visualization purposes. Uses [UMAP](https://umap-learn.readthedocs.io/en/latest/index.html#) for dimensionality reduction.
6. `make quartiles`: Compute quartiles for each cluster based on the player population it contains.
7. `make appdata`: build application data and database from analytic results. By default, this target will launch a [MongoDB](https://www.mongodb.com/) instance inside a [Docker](https://www.docker.com/) container at the URL `localhost:27017`. If the environment variable `OSRS_MONGO_URI` is set, the Mongo instance will run at that URL instead.

Steps 2-4 can be skipped by simply running `make download`, which fetches the scraped data and clustering results from an S3 bucket.

All steps can be run in one shot via `make build` (which starts from pre-downloaded data) or `make all` (which actually scrapes and clusters the data from scratch).

To launch the application, run `make app` and visit the URL `localhost:8050` in a web browser. The application expects to find the Mongo instance running at `localhost:27017` (or the environment variable `OSRS_MONGO_URI`, if set).

Run `make help` to see a list of all top-level targets.

Dependencies
------------

* Python 3.7+ (download [here](https://www.python.org/downloads/))
* Docker (download [here](https://docs.docker.com/get-docker/))

Methods
-------

* Data were scraped for the top 2 million players on the OSRS hiscores.
* Account data was deduplicated, sorted and subsampled to take skill level columns only.
* Accounts were segmented into 2000 clusters based on similarity of skills for three different splits:
  * 'all': all 23 OSRS skills
  * 'cb': the 7 combat skills
  * 'noncb': the 16 non-combat skills
* For each split of the dataset, clustering resulted in a cluster ID for each player and a set of cluster centroids.
* Cluster centroids were projected from their ambient dimensionality to 3D space.
* Quartiles (0, 25, 50, 75 and 100th percentiles) in each skill were computed based on the accounts in each cluster.
* The results are assembled into application data. Player stats are written to a database to provide stat and cluster lookups. The cluster centroids are visualized in a 3D scatterplot. Quartile ranges for individual clusters are presented in a boxplot. Cluster stats and player stats can be compared side-by-side in two tables.

Other notes
-----------

Free ideas for future work:

* Run the same analysis on the Ironman hiscores.
* Attempt to identify clusters of bot accounts within the dataset.
* Try to predict an unknown skill given all other skills for an account.
* Perform hierarchical clustering to identify super-clusters, or to explore fine-grained structure within clusters.

If scraping hiscores data for a prolonged period of time, you may get blocked due to the high volume of requests. For this reason it is recommended that you use a small number of workers if scraping 25000+ records. There is an option to proxy requests through a VPN using the flag `--vpn`, but this requires access to an OpenVPN-based service and some advanced setup. Please respectful of Jagex's server resources in your usage of this code.
