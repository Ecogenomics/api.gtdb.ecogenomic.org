from scipy.cluster.hierarchy import linkage, dendrogram


def cluster_matrix(arr, method='average'):
    # do not use  ‘centroid’, ‘median’, and ‘ward’
    linkage_y = linkage(arr, method, optimal_ordering=True)
    dendro_y = dendrogram(linkage_y)

    arr_t = arr.T
    linkage_x = linkage(arr_t, method, optimal_ordering=True)
    dendro_x = dendrogram(linkage_x)

    arr = arr[dendro_y['leaves'], :]
    arr = arr[:, dendro_x['leaves']]

    return arr, dendro_x, dendro_y
