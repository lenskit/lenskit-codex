#!/usr/bin/env -S guarsh -U
#USAGE flag="-v --verbose" help="Enable verbose logging messages."

# Code for understanding available models and pipelines.
package provide models 0.1
package require missing
package require logging
package require path

# Ensemble command for listing and querying recommender models
namespace eval ::model {
    proc list {args} {
        set data {}
        while {![lempty $args]} {
            set arg [lshift args]
            switch -glob -- $arg {
                -enabled {
                    set data [lshift args]
                }
                default {
                    error "unrecognized argument $arg"
                }
            }
        }
        set root [path resolve !/models]
        msg -debug "scanning for models in $root"
        set files [glob -directory $root -tails */pipeline.toml]
        msg -debug "found [llength $files] models"
        set models [lmap pf $files {file dirname $pf}]
        if {$data ne ""} {
            set models [lmap m $models {
                if {![enabled $m $data]} {
                    continue
                }
                set _ $m
            }]
        }
        return $models
    }

    # Query if this model is enable for this dataset
    proc enabled {model data} {
        set wanted 1
        set info {}

        set fn [path resolve "!/models/$model/info.toml"]
        if {[file exists $fn]} {
            msg -debug "reading $fn"
            set info [parse toml -file $fn]
        }

        if {[dict exists $info match include]} {
            msg -debug "checking include matches for $model on $data"
            set wanted 0
            foreach pat [dict get $info match include] {
                if {[string match $pat $data]} {
                    msg -debug "data $data matched include pattern $pat for $model"
                    set wanted 1
                    break
                }
            }
        }
        if {[dict exists $info match exclude]} {
            msg -debug "checking exclude matches for $model on $data"
            foreach pat [dict get $info match exclude] {
                if {[string match $pat $data]} {
                    msg -debug "data $data matched include pattern $pat for $model"
                    set wanted 0
                    break
                }
            }
        }
        return $wanted
    }

    # Query whether the specified model is a rating predictor.
    proc predicts-ratings {name} {
        set file [path resolve "!/models/$name/pipeline.toml"]
        set pipe [parse yaml -file $file]
        set base [dict get $pipe options base]
        return [expr {$base eq "std:topn-predict"}]
    }

    # Query whether searching is defined for this model.
    proc searchable {name} {
        set search [path resolve "!/models/$name/search.toml"]
        return [file exists $search]
    }

    namespace export list searchable predicts-ratings enabled
    namespace ensemble create
}

if {[info exists argv0]} {
    if {$argv0 eq [info script]} {

        msg "showing model list"
        foreach m [model list] {
            puts $m
        }
    }
}
