#!/bin/bash
#MISE description="fetch assets needed for web build to public repo"
#USAGE flag "-r --remote <remote>" default="public" help="specify the remote to fetch from"

set -eo pipefail

echo 'pulling static images'
dvc push -j4 --no-run-cache -r $usage_remote -R images
echo 'pulling page outputs'
dvc push -j4 --no-run-cache -r $usage_remote dvc.yaml
