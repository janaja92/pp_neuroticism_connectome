#!/bin/bash

N_JOBS=54
sbatch -p rosa_express.p --array=1-$N_JOBS fc_measures.job