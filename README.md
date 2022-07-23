osrs-hiscores
=============

A quantitative analysis of the Old School Runescape hiscores.

This repository contributes the following:

1. Code for web scraping the OSRS hiscores, along with the resulting dataset.
2. Code for a machine learning pipeline which clusters the player population by account similarity.
3. An interactive [web application](www.osrs-hiscores-explorer.com) for visualizing player results.

The dataset consists of the following files:

1. `player-stats.csv`: Skill levels in all 23 skills for the top 2 million OSRS accounts.
2. `cluster-centroids.csv`: Central values for clusters that emerge from partitioning player dataset into groups based on account similarity. Each centroid is a vector of values between 1-99 in "OSRS skill" space.
3. `player-clusters.csv`: Cluster IDs per player for three separate clustering runs, grouping similar accounts by looking at (i) all skills, (ii) combat skills only and (iii) non-combat skills only.
4. `player-stats-raw.csv`: Rank, level, xp, clues, minigame and boss stats for the top 2 million OSRS players. This file is the raw output from the scraping process (1.7 GB).

These files are **not checked in to the repo** due to file size constraints. They can be downloaded separately from Google Drive: <https://bit.ly/osrs-hiscores-dataset>

Player stats were collected from the [official OSRS hiscores](https://secure.runescape.com/m=hiscore_oldschool/overall) over a 24-hour period on July 21, 2022.

Project organization
--------------------

    ├── LICENSE
    ├── Makefile         <- Top-level Makefile for building and running project.
    ├── README.md        <- The top-level README for developers using this project.
    │
    ├── app              <- Application code and assets.
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
    │   ├── analysis     <- Data science and analytics.
    │   └── scrape       <- Scraping hiscores data.
    │
    ├── test             <- Unit tests.
    │
    ├── Procfile         <- Entry point for deployment as a Heroku application.
    ├── requirements.txt <- Dependencies file for reproducing the project environment.
    ├── runapp.py        <- Main script for Dash application.
    └── setup.py         <- Setup file for installing this project through pip.

Usage
-----

At a high level, this repository implements a data science pipeline:

    ```
    scrape OSRS hiscores data
             ↓
    cluster players by stats
             ↓
    project clusters to 3D
             ↓
    build application data
    ```

along with a [Dash](https://plotly.com/dash/) application for visualizing the results.

The stages of the data pipeline are driven by a [Makefile](https://opensource.com/article/18/8/what-how-makefile) with top-level `make` targets for each processing stage:

1. `make init`: set up project environment and install dependencies.
2. `make scrape`: scrape data from the official OSRS hiscores and transform into a cleaned dataset.
3. `make cluster`: cluster players into groups of similar accounts according to their stats. Uses [k-means](https://en.wikipedia.org/wiki/K-means_clustering) as the clustering algorithm, implemented by the [faiss](https://github.com/facebookresearch/faiss) library.
4. `make postprocess`: project the cluster centroids from high-dimensional space to 3D for visualization purposes ([UMAP](https://umap-learn.readthedocs.io/en/latest/index.html#) is the algorithm used for dimensionality reduction). Compute quartiles for each cluster based on the player population it contains.
5. `make build-app`: build application data and database using all previous analytic results. This target will launch a [MongoDB](https://www.mongodb.com/) instance inside a [Docker](https://www.docker.com/) container at the URL `localhost:27017` (by default).

Steps 2 and 3 can (and should) be skipped by simply running `make download-dataset`, which fetches the scraped data and clustering results from an S3 bucket. This requires an [AWS](https://aws.amazon.com/) account with credentials located in the `~/.aws` directory.

To launch the application, run `make run-app` and visit the URL `localhost:8050` in a web browser.

The final application can be built and run in one shot via `make app`, which uses pre-downloaded data rather than scraping and clustering the data from scratch. The target `make all` is what was used to build results for the production app.
If scraping data, note that high usage of the hiscores API may result in your IP being blocked. Please be sparing and respectful of Jagex's server resources in your usage of this code.

Run `make help` to see more top-level targets.

Configuration
-------------

A number of environment variables are used to configure the application.

* `OSRS_APPDATA_URI`: path to application data .pkl file (S3 or local)
* `OSRS_MONGO_URI`: URL at which MongoDB instance is running
* `OSRS_MONGO_COLL`: store/retrieve player data from collection with this name

There are also environment variables defining filenames at each stage of the data pipeline.

Defaults for these variables are defined in `.env.default` and imported whenever a `make` target is run. If a file called `.env` exists, any settings there will override those in `.env.default`.

Dependencies
------------

* Python 3.9 or greater (download [here](https://www.python.org/downloads/))
* Docker (download [here](https://docs.docker.com/get-docker/))
* AWS account with credentials installed in `~/.aws` directory (a free tier account can be created [here](https://aws.amazon.com/free))

Methods
-------

* Data were scraped for the top 2 million players on the OSRS hiscores. Data consists of xp, rank, and level in each OSRS skill and overall, along with rank and score stats for clue scrolls, minigames and bosses.
* Account data were deduplicated, sorted and subsampled to keep skill level columns only. After deduplication, 1999625 records remained. Each record is a length-23 vector giving an account's levels in the 23 OSRS skills.
* Accounts were segmented into 2000 clusters based on similarity of skills for three different sets of feature columns, or 'splits', of the dataset:
  * `all`: all 23 OSRS skills
  * `cb`: the 7 combat skills
  * `noncb`: the 16 non-combat skills
* For each split of the dataset, clustering resulted in a set of 2000 cluster centroids (with dimensionality 23, 7 or 16) and a cluster ID associated with each player. Clustering was performed with a standard implementation of k-means using the L2 distance.
* Cluster centroids were projected from their ambient dimensionality to 3D space using UMAP. Splits `all` and `noncb` used UMAP parameters `n_neighbors=10,  min_dist=0.25`; split `cb` used `n_neighbors=20, min_dist=0.25`.
* Quartiles (the 0, 25, 50, 75 and 100th percentiles) in each skill were computed by aggregating the accounts belonging to each cluster.
* The clustering results were assembled into a serialized data file. Player stats were written to a database to provide quick result lookups. The final application makes use of these two resources.

Project ideas
-------------

Here are some ideas for data science projects.

* Run the same analysis on the OSRS Ironman hiscores.
* Create a method for identifying bot clusters within the dataset.
* See how well you can predict one unknown skill given all other skills for an account. Is it easier for some skills than others, and can this be explained in terms of the game meta?
* Perform hierarchical clustering to identify super-clusters or search for fine-grained structure within clusters. Annotating these clusters would be a step toward a true taxonomy of OSRS accounts.
* Create a reverse lookup tool which, given a username, finds other accounts with similar stats.
