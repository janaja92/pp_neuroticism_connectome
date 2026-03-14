"""
Title: fc_measures
------------------

This script serves as the core part for the MRI pipeline. 
Designed for parallelized execution on a High-Performance Computing (HPC) 
cluster, it processes assigned subject batches to perform NIfTI parcellation 
and extract comprehensive brain network metrics.

The script calculates nine distinct static and dynamic FC measures:
    - Global Efficiency
    - Small-world Propensity
    - Average Clustering Coefficient
    - Global Strength
    - Betweenness Centrality
    - Participation Coefficient
    - Mean BOLD Variability
    - Global Efficiency Variability
    - Mean Edge Variability

Input: A batch-specific text file containing subject IDs.
Output: A  CSV file containing the calculated measures for 
        all subjects within the processed batch.
 """

import os
import argparse
import numpy as np
import pandas as pd
import nibabel as nib
from tqdm import tqdm
from comet import cifti, connectivity, graph

np.random.seed(42)

# Paths 
# IMPORTANT: Update both paths below for your environment.
# WORK_DIR: Root directory containing your scripts folder (with .py, .sh, and .job files).
# MRI_BASE_DIR: Path to the neuroimaging data; must contain subject-named folders (e.g., 'SUBJ_ID/').
WORK_DIR = "/YOUR/WORK/DIR/CONTAINING/THE/SCRIPTS/FOLDER"
MRI_BASE_DIR = f"/YOUR/PATH/TO/MRI/RESTINGSTATE/DATA"
MRI_REL_PATH = "MNINonLinear/Results/rfMRI_REST/rfMRI_REST_Atlas_MSMAll_hp2000_clean_rclean_tclean.dtseries.nii"
RESULTS_DIR = f"{WORK_DIR}/results"

# Atlas parameters
N_TIMEPOINTS = 4800
CORTICAL_RES = 200
SUBCORTICAL_RES = 54
ATLAS_NAME = f"schaefer_{CORTICAL_RES}_cortical"
N_PARCELS = CORTICAL_RES + SUBCORTICAL_RES if "subcortical" in ATLAS_NAME else CORTICAL_RES

# Analysis parameters
DENSITIES = [0.1, 0.2, 0.3, 0.4, 0.5]
WINDOWSIZE = 83 # 60sec/0.72
STEPSIZE = 10
EPSILON = 0.01 # torelance needed to account for rounding errors


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sublist",  required=True, help="Path to subject list file.")
    return p.parse_args()


def main():
    # Parse command line arguments
    args = parse_args()
    sublist = args.sublist

    # Get job number 
    task_id = os.environ.get("SLURM_ARRAY_TASK_ID", "single")

    # Load list of subjects
    subject_list = np.loadtxt(sublist, dtype=str).tolist()
    if isinstance(subject_list, str):
        subject_list = [subject_list]

    # Pre-allocate result arrays
    static_measures = np.full((len(subject_list), 30), np.nan) # 6 metrics * 5 densities
    dynamic_measures = np.full((len(subject_list), 7), np.nan) # 1 metric * 5 densities + 2 metrics

    # Loop over subjects, parcellate and calculate FC brain measures
    for i, subject in enumerate(tqdm(subject_list)):
        file_path = f"{MRI_BASE_DIR}/{subject}/{MRI_REL_PATH}" 

        try:
            # Check for missing cifti data
            if not os.path.exists(file_path):
                print(f"MISSING: {file_path}")
                continue

            # Load data and parcellate
            cifti_data = nib.load(file_path).get_fdata(dtype='float32')
            timeseries = cifti.parcellate(cifti_data, atlas=ATLAS_NAME, standardize=True)
            
            # Skip subject if it contains ANY nan
            if np.isnan(timeseries).any(): 
                print(f"CONTAINED NAN: {file_path}")
                continue

            # Calculate static FC
            sFC = connectivity.Static_Pearson(timeseries, diagonal=0, fisher_z=True).estimate()
            sFC_noneg = graph.handle_negative_weights(sFC, type="discard")

            # Loop over densitiy range and calculate static measures dependent on thresholded FC matrices
            for j, dens in enumerate(DENSITIES):  
                sFC_thresh = graph.threshold(sFC_noneg, type="density", density=dens)

                static_measures[i,j] = graph.efficiency(sFC_thresh, local=False) # Static Global Efficiency
                static_measures[i,j+5] = graph.small_world_propensity(sFC_thresh)[0] # Static Small-World-Propensity
                static_measures[i,j+10] = graph.avg_clustering_onella(sFC_thresh) # Static Mean Clustering Coefficient
                static_measures[i,j+15] = np.mean(np.sum(sFC_thresh, axis=0)) # Static Global Strength
                static_measures[i,j+20] = np.mean(graph.betweenness(sFC_thresh)) # Static Betweenness Centrality
                static_measures[i,j+25] = np.mean(graph.participation_coef(sFC_thresh, ci="louvain", degree="undirected")) # Static Participation Coefficient

            dynamic_measures[i,0] = np.mean(np.std(timeseries, axis=0)) # Dynamic Mean BOLD Variability

            # Calculate dynamic FC
            sw = connectivity.SlidingWindow(timeseries, windowsize=WINDOWSIZE, stepsize=STEPSIZE, shape="gaussian", fisher_z=True)
            dFC = sw.estimate()
            dFC_noneg = graph.handle_negative_weights(dFC, type="discard")

            # Loop over densitiy range and calculate dynamic global eff var dependent on thresholded FC matrices
            for j, dens in enumerate(DENSITIES):  
                dFC_thresh = graph.threshold(dFC_noneg, type="density", density=dens)
                
                # density check
                actual_densities = graph.density_und(dFC_thresh)[0]
                if np.any(actual_densities < (dens - EPSILON)): # warning if ANY window is below the desired density
                    min_dens = np.min(actual_densities)
                    bad_count = np.sum(actual_densities < (dens - EPSILON))
                    total_windows = actual_densities.shape[0]    
                    print(f"WARNING: Subject {subject}, Target {dens}: "
                            f"{bad_count}/{total_windows} windows dropped below target density. "
                            f"Lowest density found: {min_dens:.3f}")

                # Global Efficiency Variability
                dynamic_efficiency = []
                num_windows = dFC_thresh.shape[2] # loop through 3rd dimension
                for t in range(num_windows):
                    window_matrix = dFC_thresh[:,:,t]
                    eff = graph.efficiency(window_matrix, local=False)
                    dynamic_efficiency.append(eff)
                efficiency_var = np.std(dynamic_efficiency)
                dynamic_measures[i,1+j] = efficiency_var

            # Mean Edge Variability
            n_parcels = timeseries.shape[1]
            triu_indices = np.triu_indices(n=n_parcels, k=1)
            edge_time_series = dFC[triu_indices[0], triu_indices[1], :]
            edge_variability = np.std(edge_time_series, axis=1) # multiple edge variabilities
            mean_edge_variability = np.mean(edge_variability) # scalar: global fluidity score over all edges
            dynamic_measures[i,6] = mean_edge_variability
        
        except Exception as e:
            print(f"ERROR: Could not calculate measures {file_path} for subject {subject}. Exception: {e}")

    print(static_measures.shape)
    print(dynamic_measures.shape)
    print("Successfully constructed result arrays")


    # Wrap the arrays in one dataframe:
    # Densities (floats) to string labels
    dens_labels = [f"d{int(d*100):02d}" for d in DENSITIES]
    # Static measures col names
    cols_static = []
    cols_static.extend([f"Stat_Eff_{d}"   for d in dens_labels]) 
    cols_static.extend([f"Stat_SWP_{d}"   for d in dens_labels]) 
    cols_static.extend([f"Stat_Clust_{d}" for d in dens_labels]) 
    cols_static.extend([f"Stat_Stre_{d}"   for d in dens_labels])
    cols_static.extend([f"Stat_Betw_{d}" for d in dens_labels])
    cols_static.extend([f"Stat_Part_{d}" for d in dens_labels]) 
    # Dynamic measures col names
    cols_dynamic = ["Dyn_MeanBOLD_Var"]                          
    cols_dynamic.extend([f"Dyn_EffVar_{d}" for d in dens_labels]) 
    cols_dynamic.append("Dyn_MeanEdge_Var")
    # Separate dfs       
    df_stat = pd.DataFrame(static_measures, columns=cols_static)
    df_dyn  = pd.DataFrame(dynamic_measures, columns=cols_dynamic) 
    # Merge into one df
    final_brain_df = pd.concat([df_stat, df_dyn], axis=1)
    # Insert subject IDs as first col
    final_brain_df.insert(0, "Subject", subject_list)


    # Save the dataframe
    filename = f"brain_measures_{task_id}_{subject_list[0]}_to_{subject_list[-1]}.csv" # file name contains first and last subj ID
    full_path = f"{RESULTS_DIR}/{filename}"
    os.makedirs(RESULTS_DIR, exist_ok=True) # create folder if not already existing
    final_brain_df.to_csv(full_path, index=False) # save the df as csv without index col
    
    print(f"Successfully saved dataframe to:\n{full_path}")
    print(f"DONE: Finished {len(subject_list)} subjects from {args.sublist}.")



if __name__ == "__main__":
    main()