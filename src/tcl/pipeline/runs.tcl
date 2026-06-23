# Code for managing individual runs and generating their DVC output
package provide runs 0.1
package require parse

# define "run" - an ensemble command to generate stages for
# recommender system runs.
namespace eval ::run {
    variable info
    array set info {}

    proc begin-set {name split} {
        variable info

        set info(name) $name
        set info(split) $split
        set info(runs) [list]

        # figure out what kind of split we have
        set split_spec "splits/$split.toml"
        if {[file exists $split_spec]} {
            # this is a split specified in toml
            set info(split_in) $split_spec
            set split_info [parse toml $split_spec]
            if {[dict get $split_info method] eq "crossfold"} {
                # crossfold requires the parquet file
                set info(split_deps) [list dataset splits/$split.parquet]
            } else {
                # temporal is split on the fly
                set info(split_deps) [list dataset splits/$split.toml]
            }
        } else {
            # this is a fixed-directory split
            set info(split_in) splits/$split
            set info(split_deps) splits/$split
        }
    }

    proc default {model} {
        variable info
        set run [subst {
            args {}
            model $model
            variant default
            deps {}
        }]
        return [append $run]
    }

    proc tuned {model {tuner optuna}} {
        variable info
        set params "sweeps/$info(split)/$model-$tuner-pipeline.json"
        set run [subst {
            args {--pipeline-file $params}
            model $model
            variant $tuner-tuned
            deps $params
        }]
        return [append $run]
    }

    proc append {run} {
        variable info
        dict with run {
            set name "$model-$variant"
        }
        lappend info(runs) $name $run
        emit-stage $name $run
        return $name
    }

    # write the stage to go with a run
    proc emit-stage {name run} {
        variable info

        dict with run {
            set path "$info(split)/$model-$variant"

            stage "run-$info(split)-$name" {
                cmd lenskit codex generate {*}$args --ds-name=$info(name) --split=$info(split_in) -o runs/$path $model
                out runs/$path
                # TODO add pipeline dep
                dep {*}$info(split_deps)
                dep {*}$deps
            }
        }
    }

    # get the list of run names
    proc names {} {
        variable info
        return [dict keys $info(runs)]
    }

    # create a stage to collect the runs
    proc collect {} {
        variable info
        stage collect-metrics {
            cmd lenskit codex collect metrics -S run-summary.csv -U run-user-metrics.parquet -L runs/manifest.csv
            out run-summary.csv
            out run-user-metrics.parquet
            dep runs/manifest.csv
            foreach run [names] {
                dep runs/$info(split)/$run
            }
        }
    }

    # save the "run manifest" - a CSV of run definitions
    proc save-manifest {} {
        variable info
        file mkdir runs
        set fh [open runs/manifest.csv w]
        puts $fh "path,split,variant,model"
        foreach {name run} $info(runs) {
            dict with run {
                puts $fh "$info(split)/$model-$variant,$info(split),$variant,$model"
            }
        }
        close $fh
    }

    # list of subcommands we export from the "run" command
    namespace export begin-set default tuned names collect save-manifest
    namespace ensemble create
}
