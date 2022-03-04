import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.getcwd()), '.env'))
from api.controller.species import c_species_heatmap

from api.db import GtdbSession, GtdbWebSession

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def get_data():
    gtdb_web_db = GtdbWebSession()
    try:
        gtdb_db = GtdbSession()
        try:
            return c_species_heatmap('s__Rhizobium leguminosarum', gtdb_web_db, gtdb_db)
        finally:
            gtdb_db.close()
    finally:
        gtdb_web_db.close()


def data_to_np(data):
    label_to_idx = dict()
    idx_to_label = list()
    for i, label in enumerate(sorted(set(data.xLabels))):
        label_to_idx[label] = i
        idx_to_label.append(label)

    np_data = np.zeros((len(idx_to_label), len(idx_to_label)))

    for q, r, ani, n_frag, n_total in data.data:
        q_idx = label_to_idx[q]
        r_idx = label_to_idx[r]
        new_ani =  max(ani, np_data[q_idx, r_idx], np_data[r_idx, q_idx])
        np_data[q_idx, r_idx] = new_ani
        np_data[r_idx, q_idx] = new_ani


    return np_data, idx_to_label, label_to_idx


def main():
    data = get_data()

    np_data, idx_to_label, label_to_idx = data_to_np(data)

    # mask = np.zeros_like(np_data, dtype=np.bool)
    # mask[np.triu_indices_from(mask)] = True

    ax = sns.clustermap(np_data,
                   cmap='viridis',
                   vmin=95,
                   vmax=100,
                   # mask=mask,
                   )
    plt.show()
    return


if __name__ == '__main__':
    main()
