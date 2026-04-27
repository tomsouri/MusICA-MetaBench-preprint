#!/bin/bash

.venv/bin/python3 aggregate_results_for_determining_benchmark_size.py --all

.venv/bin/python3 test_normality.py normal

.venv/bin/python3 pairwise_significance.py --results-dir aggregated/10-times-runs/normal/ --output-dir aggregated/pairwise-significance --effect-sizes 1 1.5 2 2.5 3 3.5 4 4.5 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 25 30 35 40 45 50 75 --alpha 0.05 --shift-to-ensure-difference --bonferroni

.venv/bin/python3 pairwise_significance.py --results-dir aggregated/10-times-runs/normal/ --output-dir aggregated/pairwise-significance --effect-size 5 --alpha 0.05 --bonferroni