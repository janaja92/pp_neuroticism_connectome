# A Neural Signature of Neuroticism?
**Exploring the Functional Connectome to Predict Personality**

Welcome to the supplementary material repository for my practical project!

This repository contains the more detailed workflow, pipelines, and supplementary materials associated with my poster presentation. 

## 🔐 Open Data (Protected Access)
This project utilizes the **Human Connectome Project** Young Adult dataset (2025 Release). Specifically, this project utilizes:
- Resting State fMRI 3T Preprocessed (Recommended) neuroimaging data and
- Restricted Access Behavioral Data (.csv)


📝 Data Access
To obtain these data, researchers must apply for access via the [HCP Restricted Access application](https://www.humanconnectome.org/study/hcp-young-adult/document/restricted-data-usage); once permissions are granted, the datasets can be accessed and downloaded through the [BALSA database](https://balsa.wustl.edu/).


## 📂 Open Materials / Repository Structure
Here you can find the detailed materials for my project pipeline. Navigate through the folders below to see the specific steps:
* **`/neuro_data_prep`**: Neuroticism data preparation
* **`/measurement_models`**: Code and results for the tested measurement models
* **`/brain_pipeline`**: The brain measure calculation pipeline
* **`/integrated_sem`**: SEM (Structural Equation Modeling) results, outputs, and visualizations

For a complete visual guide to the repository's logic - from raw data to final SEM results - see this Workflow Map:

![Map of Materials](materials_map.png)
(click to enlarge)

## 🛠️ Tools & Technologies
* **Environment:** Jupyter Notebooks
* **Languages:** Python, R
* **Neuroimaging:** Comet Toolbox
* **Statistical Modeling:** `mirt`, `lavaan`
* **Integration:** `rpy2`