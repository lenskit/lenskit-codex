#!/bin/bash
#MISE description="render the seb site"
#USAGE flag "--debug" help="include debug output"

set -eo pipefail
declare -a qr_args=()

if [[ $usage_debug || $GITHUB_DEBUG ]]; then
    qr_args+="--log-level=debug"
    set -x
fi

quarto render "${qr_args[@]}"
