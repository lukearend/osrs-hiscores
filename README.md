osrs-hiscores
=============

A quantitative analysis of the OSRS hiscores, complete with open-source dataset and code.

This repository is accompanied by three important data files:

1. `player-stats.csv`: Rank, levels, xp, clues and achievements stats for the top \~2 million OSRS players.
2. `cluster-centroids.csv`: Central values for clusters that emerge from partitioning player dataset into groups based on account similarity. Each centroid is a vector of values between 1-99 in "OSRS skill" space.
5. `player-clusters.csv`: Cluster IDs per player for three separate clustering runs, grouping similar accounts according to (i) all skills, (ii) combat skills only and (iii) non-combat skills only.

These files are **not included in the repo** due to file size restraints, and must be downloaded separately from the following public Google Drive folder: <https://drive.google.com/drive/folders/***REMOVED***?usp=sharing>

Player stats were scraped from the [official OSRS hiscores](https://secure.runescape.com/m=hiscore_oldschool/overall) on Dec 28, 2021 between 00:00 and 18:00 CST.

Project organization
--------------------

    ├── LICENSE
    ├── README.md        <- The top-level README for developers using this project.
    │
    ├── Makefile         <- Top-level Makefile for building and running project.
    │
    ├── app              <- Dash application for visualizing final results.
    │   ├── callbacks    <- Dynamic behavior of application elements.
    │   ├── data         <- Data loading and processing.
    │   ├── figures      <- Plotly figures and graphical elements.
    │   └── layout       <- Global layout of application page.
    │
    ├── bin              <- Utility executables.
    │
    ├── data
    │   ├── interim      <- Intermediate data that has been transformed.
    │   ├── processed    <- The final, canonical data sets for modeling.
    │   └── raw          <- The original, immutable data dump.
    │
    ├── ref              <- Reference files used in data processing.
    │
    ├── src              <- Python source code for data analytics.
    │   ├── common       <- Common utilities such as data loading.
    │   ├── models       <- Scripts to run clustering and dimensionality reduction.
    │   ├── results      <- Scripts for building application data.
    │   └── scrape       <- Scripts for scraping raw hiscores data.
    │
    ├── test             <- Unit testing code.
    │
    ├── Procfile         <- Entry point for deployment as a Heroku application.
    ├── requirements.txt <- Dependencies file for reproducing the project environment.
    └── setup.py         <- Setup file for installing this project through pip.

Usage
-----

At a high level, this repository implements the following data pipeline

```
scrape hiscores data
         ↓
cluster players by stats
         ↓
project clusters to 3D
         ↓
build application data     ->     (run Dash app)
```

and source code for a [Dash](https://plotly.com/dash/) application which visualizes the clustering results.

The stages of the data pipeline are driven by a [Makefile](https://opensource.com/article/18/8/what-how-makefile) with top-level `make` targets for each data processing stage:

1. `make init`: set up Python virtual environment. This installs all dependencies for the Python code used in the project.
2. `make scrape`: scrape data from the official OSRS hiscores. The full scraping process takes about 18 hours.
3. `make cluster`: cluster players into similar groups according to their stats. The clustering algorithm used is the [faiss](https://github.com/facebookresearch/faiss) implementation of [k-means](https://en.wikipedia.org/wiki/K-means_clustering). The full clustering process (for 2 million players and several thousand clusters) takes about 4 hours on an Apple M1 processor.
4. `make dimreduce`: project cluster centroids from high-dimensional space to 3D for visualization purposes. This dimensionality reduction is done with the [UMAP](https://umap-learn.readthedocs.io/en/latest/index.html#) algorithm.
5. `make app`: build application data and database from analytic results. Expects a [MongoDB](https://www.mongodb.com/) instance running at the URI specified by the environment variable `OSRS_MONGO_URI`. A Mongo instance can be started at `localhost:27017` using the target `make mongo` (requires [Docker](https://www.docker.com/)).

Steps 2 and 3 can be skipped by simply running `make download`, which fetches the final dataset from an S3 bucket. This requires installation of the [AWS CLI](https://aws.amazon.com/cli/).

All steps can be run in one shot via `make build` (which uses the S3 download) or `make all` (which actually scrapes and clusters the data from scratch).

To launch the application, run `make run` and visit the URL `localhost:8050` in a web browser. The application expects the environment variable `OSRS_MONGO_URI_APP` to point to the database populated during `make app`.
