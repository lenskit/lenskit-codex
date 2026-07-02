# Standard pipeline definition for a MovieLens version.
#
# Before sourcing this file, set a "movielens" array with the following entries:
#
# - name
# - filename
# - split

package require dsinfo

set _tpl_dir [file dirname [info script]]

# set default values for MovieLens configuration
set _ml_defaults {
    search no
}
foreach {name value} $_ml_defaults {
    if {![info exists movielens($name)]} {
        set movielens($name) $value
    }
}

source $_tpl_dir/data.tcl
if {$movielens(search)} {
    source $_tpl_dir/searches.tcl
}
source $_tpl_dir/runs.tcl

set dsinfo [dict create name $movielens(name)]
dict lappend dsinfo models {*}[model list -enabled $movielens(name)]
dict lappend dsinfo splits $movielens(split)
dsinfo save $dsinfo
