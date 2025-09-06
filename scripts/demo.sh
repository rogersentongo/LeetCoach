#!/usr/bin/env bash
set -e
bash scripts/sync_ratings.sh
python3 leetcoach.py suggest two-sum || true
python3 leetcoach.py start two-sum --statement-file examples/two-sum.txt