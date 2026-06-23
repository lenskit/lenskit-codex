# Code for understanding available models and pipelines.
package provide models 0.1
package require logging
package require path
package require parse

# Ensemble command for listing and querying recommender models
namespace eval ::model {
    proc list {} {
        set root [path resolve -project models]
        msg -debug "scanning for models in $root"
        set files [glob -directory $root -tails */pipeline.toml]
        msg -debug "found [llength $files] models"
        return [lmap pf $files {file dirname $pf}]
    }

    # Query if this model is enable for this dataset
    proc enabled {model data} {
        set wanted 1
        set info {}

        set fn [path resolve -project models $model info.toml]
        if {[file exists $fn]} {
            msg -debug "reading $fn"
            set info [parse toml $fn]
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
        set pipe [path resolve -project models $name pipeline.toml]
        set fh [open $pipe]
        while {[gets $fh line] >= 0} {
            if {[string match *std:topn-predict* $line]} {
                return 1
            }
        }
        return 0
    }

    # Query whether searching is defined for this model.
    proc searchable {name} {
        set search [path resolve -project models $name search.toml]
        return [file exists $search]
    }

    namespace export list searchable predicts-ratings enabled
    namespace ensemble create
}

if {[info exists argv0]} {
    if {$argv0 eq [info script]} {
        package require getopt
        getopt arg $argv {
            -v - --verbose {
                # increase logging verbosity
                logging::configure -verbose
            }
        }

        msg "showing model list"
        foreach m [model list] {
            puts $m
        }
    }
}
