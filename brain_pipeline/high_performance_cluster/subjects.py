"""
Subject ID Pre-processing and Batch Generation
----------------------------------------------
This script serves as the initial preparation step for the high-performance computing (HPC) 
pipeline. Its primary function is to cross-reference the official HCP-YA restricted data 
with the available resting-state fMRI imaging directory.

The script performs an intersection to identify only those participants who 
possess both valid behavioral metadata and complete neuroimaging files. To optimize 
the subsequent parallel processing on the cluster, the script then partitions the 
resulting list of validated subject IDs into 54 separate text files. Each subset acts 
as a discrete batch, allowing for efficient, simultaneous job submission across the 
cluster's compute nodes.
"""

import os
import pandas as pd
import math

# IMPORTANT: Update the three paths below for your environment.
# data_dir: Path to the neuroimaging data; must contain subject-named folders (e.g., 'SUBJ_ID/').
data_dir = "/YOUR/PATH/TO/MRI/DATA/restingstate/"
restricted_data_dir = "/YOUR/PATH/TO/RESTRICTED/BEHAVIORAL/DATA.csv"
save_dir = "/YOUR/PATH/TO/SAVING/FOLDER/"
os.makedirs(save_dir, exist_ok=True)


# 1) Subjects with resting state data
subjects_dir = sorted([f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))])

# 2) Subjects in restricted CSV
restricted_data = pd.read_csv(restricted_data_dir)
subjects_csv = sorted(restricted_data["Subject"].astype(str).str.strip().tolist())

# 3) Sets for comparison
set_dir = set(subjects_dir)
set_csv = set(subjects_csv)

only_in_dir = sorted(set_dir - set_csv)
only_in_csv = sorted(set_csv - set_dir)
in_both = sorted(set_dir & set_csv)

print(f"Resting state:     {len(subjects_dir)}")
print(f"Restricted csv:    {len(subjects_csv)}")
print(f"Overlap:           {len(in_both)}")
print(f"Only restingstate: {len(only_in_dir)}")
print(f"Only csv:          {len(only_in_csv)}")

# 4) Save lists to text files (one subject ID per line)
out_file = os.path.join(save_dir, "subjects_all.txt")

with open(out_file, "w") as f:
    f.write("\n".join(in_both) + "\n")

print(f"\n\033[1;32mDONE: Saved {len(in_both)} subjects to {out_file}\033[0m")

# 5) Split subjects into parts for parallel processing
# returns exactly n_splits files if n is perfectly divisible by n_splits
# returns less files otherwise (fixed amount of subjects per file except for the last one)
n_splits = 55
n = len(in_both)

# for n=1071 and n_splits=55, chunk_size becomes 20 
# --> 53 chunks of 20 subjects + 1 chunk of 11 subjects
chunk_size = math.ceil(n / n_splits)

chunks = [in_both[i * chunk_size:(i + 1) * chunk_size] for i in range(n_splits)]

for i, chunk in enumerate(chunks, start=1):
    # Stop before creating empty files if we run out of subjects (e.g., if n < n_splits)
    if not chunk:
        break
        
    out_file = os.path.join(save_dir, f"subjects_part{i}.txt")
    with open(out_file, "w") as f:
        f.write("\n".join(chunk) + "\n")
    
    # Print progress per file
    print(f"Saved part {i}: {len(chunk)} subjects")

print(f"\n\033[1;32mDONE: Processed {n} subjects into {i} files.\033[0m")