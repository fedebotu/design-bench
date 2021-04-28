from design_bench import DATA_DIR
from design_bench import maybe_download
import pandas as pd
import numpy as np
import argparse
import os
import math


if __name__ == "__main__":

    parser = argparse.ArgumentParser("Process Raw Superconductor")
    parser.add_argument("--shard-folder", type=str, default="./superconductor")
    parser.add_argument("--samples-per-shard", type=int, default=5000)
    args = parser.parse_args()

    # download the gfp dataset if not already
    maybe_download('1_jcPkQ-M1FRhkEONoE57WEbp_Rivkho2',
                   os.path.join(DATA_DIR, 'gfp_data.csv'))

    # download the gfp dataset if not already
    maybe_download('1AguXqbNrSc665sablzVJh4RHLodeXglx',
                   os.path.join(DATA_DIR, 'superconductor_unique_m.csv'))

    # load the static dataset
    df = pd.read_csv(os.path.join(
        DATA_DIR, 'superconductor_unique_m.csv'))

    # extract the relative mix of chemicals whose composition leads
    # to a superconducting material as a particular critical temperature
    x = df[df.columns[:-2]].to_numpy(dtype=np.float32)

    # extract the critical temperatures for each material
    y = df["critical_temp"] \
        .to_numpy(dtype=np.float32).reshape((-1, 1))

    # calculate the number of batches per single shard
    batch_per_shard = int(math.ceil(
        y.shape[0] / args.samples_per_shard))

    # loop once per batch contained in the shard

    os.makedirs(args.shard_folder, exist_ok=True)
    for shard_id in range(batch_per_shard):

        # slice out a component of the current shard
        x_sliced = x[shard_id * args.samples_per_shard:
                     (shard_id + 1) * args.samples_per_shard]
        y_sliced = y[shard_id * args.samples_per_shard:
                     (shard_id + 1) * args.samples_per_shard]

        np.save(os.path.join(
            args.shard_folder,
            f"superconductor-x-{shard_id}.npy"), x_sliced)

        np.save(os.path.join(
            args.shard_folder,
            f"superconductor-y-{shard_id}.npy"), y_sliced)