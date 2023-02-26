

They technically do two different things.

min_samples = the minimum number of neighbours to a core point. The higher this is, the more points are going to be discarded as noise/outliers. This is from DBScan part of HDBScan.

min_cluster_size = the minimum size a final cluster can be. The higher this is, the bigger your clusters will be. This is from the H part of HDBScan.

Increasing min_samples will increase the size of the clusters, but it does so by discarding data as outliers using DBSCAN.

Increasing min_cluster_size while keeping min_samples small, by comparison, keeps those outliers but instead merges any smaller clusters with their most similar neighbour until all clusters are above min_cluster_size.

So:

    If you want many highly specific clusters, use a small min_samples and a small min_cluster_size.
    If you want more generalized clusters but still want to keep most detail, use a small min_samples and a large min_cluster_size
    If you want very very general clusters and to discard a lot of noise in the clusters, use a large min_samples and a large min_cluster_size.

(It's not possible to use min_samples larger than min_cluster_size, afaik)
