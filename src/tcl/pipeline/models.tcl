# Code for understanding available models and pipelines.
package provide models 0.1
package require logging
package require path

namespace eval ::model {
    proc list {} {
        set root [path resolve -project models]
        msg -debug "scanning for models in $root"
        set files [glob -directory $root -tails */pipeline.toml]
        msg -debug "found [llength $files] models"
        return [lmap pf $files {file dirname $pf}]
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

    namespace export list searchable predicts-ratings
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
