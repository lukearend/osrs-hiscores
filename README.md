osrs-hiscores
=============

A quantitative analysis of the OSRS hiscores, complete with open-source dataset and code.

Project organization
--------------------

    ├── LICENSE
    ├── README.md          <- The top-level README for developers using this project.
    │
    ├── app                <- Dash application for visualizing final results.
    │
    ├── data
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    │
    ├── figures            <- Graphics and figures generated from the data.
    ├── notebooks          <- Jupyter notebooks for exploring data and generating figures.
    ├── reference          <- Reference files used in data processing.
    │
    ├── src                <- Python source code for this project.
    │   ├── data           <- Scripts to download, generate and/or clean data.
    │   ├── features       <- Scripts to turn raw data into features for modeling.
    │   ├── models         <- Scripts to train and use machine learning models.
    │   └── visuals        <- Scripts to create exploratory visualizations.
    │
    ├── Makefile           <- Top-level Makefile for building and running project.
    ├── requirements.txt   <- Dependencies file for reproducing the project environment.
    └── setup.py           <- Setup file for installing this project through pip.

This repo is accompanied by two important data files:

TODO: instructions for downloading both files and adding to repo under the data/processed directory.

1. `data/processed/stats.csv`: Rank, levels, xp, clues and achievements stats for the top \~2 million OSRS players. This file is *not currently in the repo* due to github file size restraints, and must be downloaded separately and added to the repo. To do this, run `wget TODO: get stats.csv from Google Drive or S3 bucket and place in repo` from the command line in this directory or (i) click TODO: [here]() to download and (ii) copy the downloaded file into the folder `data/processed/` under the this repo directory.

Usage
-----

Run `make init` to set up virtual environment. Run `make analytics` to run the full analytics pipeline on the raw data, producing final results (takes about TODO seconds on M1 mac). To launch the visualization, run `make app` and then navigate to `localhost:8050` in the browser.

The virtual environment must be activated to work interactively with python. To do this, run `source env/bin/activate` from the top-level directory. You can then open a notebook server by running `make notebook` and going to `localhost:8888` in the browser. The notebooks in this repository were used to generate the final figures.

Run `make scrape` to download and build the raw dataset by scraping official OSRS hiscores. Note: depends on the `expresso` [tool](https://github.com/sttz/expresso) for ExpressVPN.

Dependencies
------------

Needs `docker` to run MongoDB.

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
