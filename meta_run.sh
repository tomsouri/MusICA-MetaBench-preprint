#!/bin/bash
#SBATCH -J run      # name of job
#SBATCH -p cpu-ms       # name of partition or queue (default=cpu-troja)
#SBATCH -o run.out  # name of output file for this submission script
#SBATCH -e run.err  # name of error file for this submission script

run bash run-multiple-runs.sh