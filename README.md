osrs-hiscores
=============

A quantitative analysis of the OSRS hiscores, complete with open-source dataset and code.

Project organization
--------------------

    ├── LICENSE
    ├── README.md          <- The top-level README for using this project.
    ├── data
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    │
    ├── notebooks          <- Jupyter notebooks for exploring data and generating figures.
    ├── figures            <- Graphics and figures generated from the data.
    ├── reference          <- Reference files used in data processing.
    │
    ├── requirements.txt   <- The dependencies file for reproducing the project environment.
    ├── setup.py           <- Setup file for installing this project through pip.
    │
    └── hiscores           <- Python source code for this project.
        ├── data           <- Scripts to download, generate and/or clean data.
        ├── features       <- Scripts to turn raw data into features for modeling.
        ├── models         <- Scripts to train and use machine learning models.
        └── visualization  <- Scripts to create exploratory visualizations.

This repo is accompanied by two important data files:

1. `data/processed/stats.csv`: Rank, levels, xp, clues and achievements stats for the top \~2 million OSRS players. This file is *not currently in the repo* due to github file size restraints, and must be downloaded separately and added to the repo. To do this, run `wget TODO: get stats.csv from Google Drive or S3 bucket and place in repo` from the command line in this directory or (i) click TODO: [here]() to download and (ii) copy the downloaded file into the folder `data/processed/` under the this repo directory.

2. `data/processed/clusters.csv`: A segmentation of the 2 million players into several thousand distinct clusters for each of three data splits: all skills, combat skills only, non-combat skills only. These clusters are approximately equidistant in the L1 metric on vector space &#x2115;&#x00B2;&#x00B3; (integer levels for each of 23 skills) and are suitable for embedding into a lower dimensionality.

Usage
----------------------

Run `make init` to set up virtual environment. Run `make analytics` to run the full analytics pipeline on the raw data, producing final results (takes about TODO seconds on M1 mac). To launch the visualization, run `make app` and then navigate to `localhost:8050` in the browser.

The virtual environment must be activated to work interactively with python. To do this, run `source env/bin/activate` from the top-level directory. You can then open a notebook server by running `make notebook` and going to `localhost:8888` in the browser. The notebooks in this repository were used to generate the final figures.

Run `make scrape` to download and build the raw dataset by scraping official OSRS hiscores. Note: depends on the `expresso` [tool](https://github.com/sttz/expresso) for ExpressVPN.

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
