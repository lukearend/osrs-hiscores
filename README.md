osrs-hiscores
=============

A quantitative analysis of the OSRS hiscores, complete with open-source dataset and code.

This repository is accompanied by three important data files:

1. `player-stats.csv`: Rank, levels, xp, clues and achievements stats for the top \~2 million OSRS players.
2. `cluster-centroids.csv`: Central values for clusters that emerge from partitioning player dataset into groups based on account similarity. Each centroid is a vector of values between 1-99 in "OSRS skill" space.
5. `player-clusters.csv`: Cluster IDs per player for three separate clustering runs, grouping similar accounts according to (i) all skills, (ii) combat skills only and (iii) non-combat skills only.

These files are **not included in the repo** due to file size restraints, and can be downloaded separately from the following public Google Drive folder: <https://drive.google.com/drive/folders/***REMOVED***?usp=sharing>

Player stats were scraped from the [official OSRS hiscores](https://secure.runescape.com/m=hiscore_oldschool/overall) on [TODO: Dec 28, 2021 between 00:00 and 18:00 CST].

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
    ├── test             <- Unit and integration tests. Reading these may be a good
    │                       starting point for getting to know the code and pipeline.
    │
    ├── Procfile         <- Entry point for deployment as a Heroku application.
    ├── requirements.txt <- Dependencies file for reproducing the project environment.
    └── setup.py         <- Setup file for installing this project through pip.

Usage
-----

At a high level, this repository implements

1. The following data pipeline:

    ```
    scrape hiscores data
             ↓
    cluster players by stats
             ↓
    project clusters to 3D
             ↓
    build application data     ->     (run Dash app)
    ```

2. A [Dash](https://plotly.com/dash/) application which visualizes the clustering results.

The stages of the data pipeline are driven by a [Makefile](https://opensource.com/article/18/8/what-how-makefile) with top-level `make` targets for each data processing stage:

1. `make init`: set up Python virtual environment. This installs all dependencies for the Python code used in the project.
2. `make scrape`: scrape data from the official OSRS hiscores. The scraping process takes about [TODO: X] hours.
3. `make cluster`: cluster players into groups of similar accounts according to their stats. The clustering algorithm used is [k-means](https://en.wikipedia.org/wiki/K-means_clustering), implemented by the [faiss](https://github.com/facebookresearch/faiss) library. Running the clustering process for 2 million players and [TODO: k] clusters takes about [TODO: X] hours on a [TODO: x processor].
4. `make analytics`: 
   1. Map cluster centroids from a high-dimensional space to 3D for visualization purposes. Uses [UMAP](https://umap-learn.readthedocs.io/en/latest/index.html#) for dimensionality reduction.
   2. Compute quartiles for each cluster based on the player population it contains.
5. `make app`: build application data and database from analytic results. By default, this target will pull and launch a [MongoDB](https://www.mongodb.com/) instance inside a [Docker](https://www.docker.com/) container, reachable at `localhost:27017`. If the environment variable `OSRS_MONGO_URI` is set, the Mongo instance will run at that URL instead.

Steps 2 and 3 can be skipped by simply running `make download`, which fetches the scraped data and clustering results from an S3 bucket.

All steps can be run in one shot via `make build` (which uses the download) or `make all` (which actually scrapes and clusters the data from scratch).

To launch the application, run `make run` and visit the URL `localhost:8050` in a web browser. The application expects to find the Mongo instance running at `localhost:27017` or the environment variable `OSRS_MONGO_URI`, if set.

Scraping
--------

If scraping data rapidly for a prolonged period of time, your IP address may get blocked due to the high volume of requests. For this reason it is recommended that you use a small number of workers while scraping. Please be respectful of Jagex's server resources in your usage of this code.

Dead VPN description
--------------------

Prerequisites: NordVPN subscription (simple, but paid) or access to another VPN service running the OpenVPN protocol (advanced).

Data scraping makes use of OpenVPN to avoid request throttling via IP proxying. OpenVPN is an open-source protocol that allows VPN clients to communicate with VPN servers via a standardized interface. 

The OpenVPN command line client should be installed and OpenVPN server files (.opvn) to use for scraping should be placed in the directory `ref/vpn`. Authentication credentials should be placed in the file `~/.config` where the first line is the OpenVPN username and second line is the password. Throughout the scraping process, the script will periodically choose a new server file and reconnect at that IP.

This repository ships with a list of IP addresses for NordVPN servers. If you have a NordVPN account, the `~/.config` file should contain your service credentials. The scraping script will then use your service credentials to connect to the NordVPN servers listed in `bin/vpn/server-ips`. If you do not have a NordVPN account, you will have to supply OpenVPN with credentials for another VPN service that is compatible with OpenVPN. This could be a VPN server you own privately or another VPN service that uses the OpenVPN protocol. Place your service credentials in the file `~/.config` as described above and populate the file `bin/vpn/server-ips` with a list of server IPs you would like to connect to. The scraping script will then proxy through those IPs.

Scraping can be performed without using a VPN by running the scraping script with the option `--novpn`. This is not recommended as your IP address will be directly exposed to Jagex's servers. It is likely that your IP address will be blocked due to the volume of requests after a few minutes of scraping activity.

Dependencies
------------

* Python 3.[TODO]+
* Docker ([TODO: installation instructions])
* for data scraping:
  * [expresso](https://github.com/sttz/expresso) ([TODO: installation instructions)]: a command line interface to [ExpressVPN](https://www.expressvpn.com/)
  * ExpressVPN ([TODO: installation instructions])
* for developers:
  * `jq` ([TODO: installation instructions])
  * the [AWS CLI](https://aws.amazon.com/cli/) ([TODO: installation instructions])
