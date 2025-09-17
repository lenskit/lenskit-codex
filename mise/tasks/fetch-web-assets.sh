#!/bin/bash
#MISE description="fetch assets needed for web build to public repo"
#USAGE flag "-r --remote <remote>" default="public" help="specify the remote to fetch from"

set -eo pipefail
source "$MISE_PROJECT_ROOT/mise/task-functions.sh"

msg 'pulling static images'
runx dvc pull -j4 --no-run-cache -r $usage_remote -R images
msg 'pulling page outputs'
runx dvc pull -j4 --no-run-cache -r $usage_remote dvc.yaml
