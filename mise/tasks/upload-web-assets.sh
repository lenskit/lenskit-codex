#!/bin/bash
#MISE description="upload assets needed for web build to public repo"

set -eo pipefail
source "$MISE_PROJECT_ROOT/mise/task-functions.sh"

msg 'pushing static images'
runx dvc push -j4 --no-run-cache -r public -R images
msg 'pushing page outputs'
runx dvc push -j4 --no-run-cache -r public dvc.yaml
