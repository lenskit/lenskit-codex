#!/bin/zsh
#MISE description="Re-render the DVC pipelines."
#USAGE flag "-v --verbose" help="Enable verbose logging."

setopt -eo pipefail

: "${PIPE_TCL:=guarsh}"

declare -a mk_args=()

if [[ $usage_verbose ]]; then
    mk_args+=(--verbose)
fi

for file in **/pipeline.tcl; do
    dir="$(dirname "$file")"
    "${PIPE_TCL:-guarsh}" scripts/mkpipeline.tcl -- "${mk_args[@]}" -o "${dir}/dvc.yaml" "$file"
done

# FIXME Use Guardian for update-gitignore too
./scripts/update-gitignore.tcl
