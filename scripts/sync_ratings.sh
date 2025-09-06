#!/usr/bin/env bash
set -euo pipefail
mkdir -p data
# Zerotrac raw ratings
curl -L https://raw.githubusercontent.com/zerotrac/leetcode_problem_rating/main/ratings.txt \
  -o data/ratings.txt
python3 leetcoach.py build-index --ratings-file data/ratings.txt --out data/ratings.json
printf "\nSynced ratings into data/ratings.json\n"