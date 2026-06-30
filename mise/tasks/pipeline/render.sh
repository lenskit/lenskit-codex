#!/bin/zsh
#MISE description="Re-render the DVC pipelines."
#USAGE flag "-v --verbose" help="Enable verbose logging."

setopt -eo pipefail

declare -a mk_args=()

if [[ $usage_verbose ]]; then
    mk_args+=(--verbose)
fi

for file in **/pipeline.tcl; do
    dir="$(dirname "$file")"
    ./scripts/mkpipeline.tcl "${mk_args[@]}" -o "${dir}/dvc.yaml" "$file"
done

"${PIPE_TCL:-guarsh}" scripts/update-gitignore.tcl
