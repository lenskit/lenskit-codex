#!/bin/bash
#MISE description="upload assets needed for web build to public repo"

set -eo pipefail

echo 'pushing static images'
dvc push -j4 --no-run-cache -r public -R images
echo 'pushing page outputs'
dvc push -j4 --no-run-cache -r public dvc.yaml
