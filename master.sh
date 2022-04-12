#!/usr/bin/env bash

for k in 100 200 500 1000 ; do
    for n_neighbors in 5 10 15 20 ; do
        for min_dist in 0.0 0.1 0.25 0.5 ; do
            export KMEANS_K=$k
            export UMAP_NN=$n_neighbors
            export UMAP_MINDIST=$min_dist
            make appdata
        done
    done
done
