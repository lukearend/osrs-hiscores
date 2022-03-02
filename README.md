osrs-hiscores
=============

A quantitative analysis of the OSRS hiscores, complete with open-source dataset and code.

This repository is accompanied by two important data files:

1. `player-stats.csv`: Rank, levels, xp, clues and achievements stats for the top \~2 million OSRS players.
2. `player-clusters.csv`: Cluster IDs per player for three separate clustering runs, grouping similar accounts according to (i) all skills, (ii) combat skills only and (iii) non-combat skills only.

These files are **not included in the repo** due to file size restraints, and must be downloaded separately from one of the following:

* Google Drive: <https://drive.google.com/drive/folders/***REMOVED***?usp=sharing>
* S3 bucket:
  * <a id="centroids-url" href="s3://osrshiscores/datasets/cluster-centroids.csv">Cluster centroids</a>
  * [s3://osrshiscores/datasets/player-stats.csv]()
  * [s3://osrshiscores/datasets/player-clusters.csv]()

The files can be downloaded programmatically by cloning this repository and running `make download`.

Player stats were scraped from the [official OSRS hiscores](https://secure.runescape.com/m=hiscore_oldschool/overall) on Dec 28, 2021 between 00:00 and 18:00 CST.

Project organization
--------------------

    ├── LICENSE
    ├── README.md        <- The top-level README for developers using this project.
    │
    ├── app              <- Dash application for visualizing final results.
    │   ├── callbacks    <- Dynamic behavior of application elements.
    │   ├── data         <- Data loading and processing.
    │   ├── figures      <- Plotly figures and graphical elements.
    │   └── layout       <- Global layout of application page.
    │
    ├── data
    │   ├── interim      <- Intermediate data that has been transformed.
    │   ├── processed    <- The final, canonical data sets for modeling.
    │   └── raw          <- The original, immutable data dump.
    │
    ├── reference        <- Reference files used in data processing.
    │
    ├── src              <- Python source code for data analytics.
    │   ├── common       <- Common utilities such as data loading.
    │   ├── models       <- Scripts to run clustering and dimensionality reduction.
    │   ├── results      <- Scripts for building application data.
    │   └── scrape       <- Scripts for scraping raw hiscores data.
    │
    ├── Makefile         <- Top-level Makefile for building and running project.
    ├── requirements.txt <- Dependencies file for reproducing the project environment.
    └── setup.py         <- Setup file for installing this project through pip.

Usage
-----

At a high level, this repository implements the following data pipeline:

```
scrape hiscores data -> cluster players -> project clusters to 3D -> build application
```

These stages are driven by a Makefile with top-level `make` targets for each data processing step:

1. `make init`: set up Python virtual environment. This installs all dependencies for the Python code used in the project.
2. `make scrape`: scrape data from the official OSRS hiscores. The full scraping process takes about 18 hours.
3. `make cluster`: cluster players into similar groups according to their stats. The clustering algorithm used is the [faiss](https://github.com/facebookresearch/faiss) implementation of [k-means](https://en.wikipedia.org/wiki/K-means_clustering).
4. `make dimreduce`: project cluster centroids from high-dimensional space to 3D for visualization purposes. This dimensionality reduction is done with the [UMAP](https://umap-learn.readthedocs.io/en/latest/index.html#) algorithm.
5. `make app`: build application data and database from analytic results. Expects a [MongoDB](TODO) instance running at the URI specified by the environment variable `OSRS_MONGO_URI`. A Mongo instance can be started at `localhost:27017` using the target `make mongo` (requires [Docker](TODO)).

Steps 1-3 can be skipped by simply running `make download`, which fetches the final dataset from an S3 bucket.

All steps can be run in one shot via `make build` (which starts from the S3 download) or `make all` (which actually scrapes and clusters the data from scratch).

To launch the application, run `make app-run` and visit the URL `localhost:8050` in a web browser. The application expects the environment variable `OSRS_MONGO_URI` to point to the database populated during `make app`.
