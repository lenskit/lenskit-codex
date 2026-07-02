#!/bin/zsh
#MISE description="Re-render the DVC pipelines."
#USAGE flag "-v --verbose" help="Enable verbose logging."
#USAGE flag "--gitignore" negate="--no-gitignore" default=#true help="Update gitignore files as well."

setopt -eo pipefail

: "${PIPE_TCL:=guarsh}"

declare -a mk_args=()

if [[ $usage_verbose ]]; then
    mk_args+=(--verbose)
fi

for file in **/pipeline.tcl; do
    dir="$(dirname "$file")"
    $PIPE_TCL scripts/mkpipeline.tcl -- --format "${mk_args[@]}" -o "${dir}/dvc.yaml" "$file"
done

if [[ $usage_gitignore = true ]]; then
    $PIPE_TCL ./scripts/update-gitignore.tcl
fi
