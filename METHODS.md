methods
=======

In this document I explain how I reached the results shown in this repository.

Data collection and cleaning
----------------------------

The front page of the Old School Runescape hiscores resides at the following URL:

https://secure.runescape.com/m=hiscore_oldschool/overall.

This is a static webpage showing the top 25 players, from ranks 1 to 25. Navigating to the next page of the hiscores (by clicking a downward arrow on the front page) gives the next 25 players, from ranks 26-50. The URL for this second page is

https://secure.runescape.com/m=hiscore_oldschool/overall?page=2.

The URL now has an HTTP query parameter `page` with the value `2`. It turns out we can modify this query paramter in the URL to go to whichever hiscores page we want. Page 1 contains player with ranks 1-25, page 2 contains ranks 26-50, 3 contains 51-75, and so forth. This goes all the way up to page 80000, giving us players 1999976-2000000, beyond which there are no more pages. Thus, it is possible to create a script that collects the usernames of the top 2 million OSRS players by doing the following for each page from 1 to 80000:

1. create URL using page number
2. download raw HTML for the webpage at URL
3. parse username/rank data out of raw HTML
4. append username/rank data to results file

This is implemented in `src/scrape/scrape_usernames.py`, which downloads many pages simultaneously using concurrent programming. The only complication is that after running for a minute or so, the requests get blocked by the hiscores server due to excessive usage. This we wrap this script in a loop which repeatedly runs the script until blocked and then switches to a new IP address using ExpressVPN. This is implemented by the make target `$(DATA_RAW)/usernames-raw.csv`, which scrapes usernames and dumps them to a CSV file in the raw data folder.

At this point we have a CSV file containing the ranked usernames of the top 2 million OSRS players. However this data is not necessarily clean: stopping and starting the script in the middle of a page write may have caused parts of some pages to be written twice, or some usernames may have been scraped twice due to live updates of the official OSRS hiscores data. We remove duplicate usernames by taking the record with the highest ranking, as this record is the latest and thus the most current. For the present dataset, deduplication resulted in 1999948 unique usernames. These remaining players were sorted (using the same sort order as the official OSRS hiscores) enumerated to provide a ranking, and written to CSV. This is implemented in `src/scrape/clean_usernames.py` and driven by the make target `$(DATA_TMP)/usernames.csv`.

Data analysis
-------------

### Histograms
### Clustering
### Dimensionality reduction
