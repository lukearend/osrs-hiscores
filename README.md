osrs-hiscores
=============

A quantitative analysis of the OSRS hiscores, complete with open-source dataset and code.

This repository is accompanied by two important data files:

1. `player-stats.csv`: Rank, levels, xp, clues and achievements stats for the top \~2 million OSRS players.
2. `player-clusters.csv`: Cluster IDs per player for three separate clustering runs, grouping similar accounts according to (i) all skills, (ii) combat skills only and (iii) non-combat skills only.

These files are **not included in the repo** due to file size restraints, and must be downloaded separately from one of the following:

* Google Drive: <https://drive.google.com/drive/folders/***REMOVED***?usp=sharing>
* S3 bucket:
  * [s3://osrshiscores/datasets/player-stats.csv]()
  * [s3://osrshiscores/datasets/player-clusters.csv]()

Player stats were scraped from the [official OSRS hiscores](https://secure.runescape.com/m=hiscore_oldschool/overall) on Dec 28, 2021 between 00:00 and 18:00 CST.

Project organization
--------------------

    ├── LICENSE
    ├── README.md        <- The top-level README for developers using this project.
    │
    ├── app              <- Dash application for visualizing final results.
    │
    ├── data
    │   ├── interim      <- Intermediate data that has been transformed.
    │   ├── processed    <- The final, canonical data sets for modeling.
    │   └── raw          <- The original, immutable data dump.
    │
    ├── figures          <- Graphics and figures generated from the data.
    ├── notebooks        <- Jupyter notebooks for exploring data and generating figures.
    ├── reference        <- Reference files used in data processing.
    │
    ├── src              <- Python source code for this project.
    │   ├── data         <- Scripts to download, generate and/or clean data.
    │   ├── features     <- Scripts to turn raw data into features for modeling.
    │   ├── models       <- Scripts to train and use machine learning models.
    │   └── visuals      <- Scripts to create exploratory visualizations.
    │
    ├── Makefile         <- Top-level Makefile for building and running project.
    ├── requirements.txt <- Dependencies file for reproducing the project environment.
    └── setup.py         <- Setup file for installing this project through pip.

Usage
-----

Run `make init` to set up virtual environment. Run `make analytics` to run the full analytics pipeline on the raw data, producing final results (takes about TODO seconds on M1 mac). To launch the visualization, run `make app` and then navigate to `localhost:8050` in the browser.

The virtual environment must be activated to work interactively with python. To do this, run `source env/bin/activate` from the top-level directory. You can then open a notebook server by running `make notebook` and going to `localhost:8888` in the browser. The notebooks in this repository were used to generate the final figures.

Dependencies
------------

* `expresso` expressVPN CLI for IP hopping in data scraping scripts
* `aws-cli`: AWS CLI for uploading scraped data
* `gdrive`: Google Drive CLI for uploading scraped data
