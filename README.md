osrs-hiscores
=============

An in-depth analysis of the OSRS hiscores, complete with open-source dataset and code.

Project organization
--------------------

    ├── LICENSE
    ├── README.md          <- The top-level README for developers using this project.
    ├── data
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    │
    ├── models             <- Trained and serialized models, model predictions, or model summaries.
    │
    ├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering)
    │   │                     and a short `-` delimited description, e.g. `1.0-explore-raw-data`.
    │   └── reports        <- Notebooks that reproduce figures in reports.
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting.
    │
    ├── reference          <- Lookup files, reference manuals, etc.
    │
    ├── requirements.txt   <- The dependencies file for reproducing the project environment.
    │
    ├── setup.py           <- Setup file for project pip install.
    │
    └── hiscores           <- Source code for use in this project.
        ├── data           <- Scripts to download or generate data.
        ├── features       <- Scripts to turn raw data into features for modeling.
        ├── models         <- Scripts to train models and use trained models to make predictions.
        └── visualization  <- Scripts to create exploratory and results oriented visualizations.

Ships with the following two important data files:

1. `data/processed/stats.csv`: Rank, levels, xp, clues and achievements stats for top 2 million OSRS players. This file is *not currently in the repo* due to github file size restraints, and must be downloaded separately and added to the repo. To do this, run `wget TODO: get stats.csv from Google Drive or S3 bucket and place in repo` or (i) click TODO: [here]() to download and (ii) copy the downloaded file into the folder `data/processed/` under the this repo directory.

2. `data/processed/clusters.csv`: A segmentation of the 2 million players into several thousand distinct clusters for each of three data splits: all skills, combat skills only, non-combat skills only. These clusters are approximately equidistant in the L1 metric on vector space &#x2115;&#x00B2;&#x00B3; (integer levels for each of 23 skills) and are suitable for embedding into a lower dimensionality.

Usage
----------------------

Run `make init` to set up virtual environment.

The virtual environment must be activated to work interactively with python. To do this, run `source env/bin/activate` in the top-level directory.

Run `make help` to see all available `make` commands. In particular:

* `make scrape`: download and build raw dataset by scraping official OSRS hiscores. Note: depends on the `expresso` [tool](https://github.com/sttz/expresso) to circumvent request throttling suppression by periodically switching IPs while scraping the data.

* `make analytics`: compute analytic results on scraped data.

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
