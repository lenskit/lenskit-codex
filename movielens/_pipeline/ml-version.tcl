# Standard pipeline definition for a MovieLens version.
#
# Before sourcing this file, set a "movielens" array with the following entries:
#
# - name
# - filename
# - split

package require dsinfo

set _tpl_dir [file dirname [info script]]

source $_tpl_dir/data.tcl
source $_tpl_dir/runs.tcl

set dsinfo [dict create name $movielens(name)]
dict lappend dsinfo models {*}[model list -enabled $movielens(name)]
dict lappend dsinfo splits $movielens(split)
dsinfo save $dsinfo
