# Standard pipeline definition for a MovieLens version.
#
# Before sourcing this file, set the following variables:
# - ml_name
# - ml_fn
# - ml_split

set _tpl_dir [file dirname [info script]]

source $_tpl_dir/data.tcl
source $_tpl_dir/runs.tcl
