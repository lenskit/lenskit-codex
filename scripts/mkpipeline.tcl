#!/usr/bin/env tclsh

package require logging
package require dvc
package require getopt

set scripts {}
set format 0
set out_file ""

getopt arg $argv {
    -v - --verbose {
        # increase logging verbosity
        logging::configure -verbose
    }
    --format {
        # format pipeline output
        set format 1
    }
    -o: - --output=FILE {
        # save pipeline to file instead of stdout
        set out_file $arg
    }

    arglist {
        set scripts $arg
    }
}

foreach script $scripts {
    msg "evaluating pipeline $script"
    ::dvc::reset
    ::dvc::eval_pipeline $script
    set pid 0
    if {$out_file ne ""} {
        msg "saving to $out_file"
        if {$format} {
            msg -debug "saving with dprint"
            set out_fh [open "|dprint fmt --stdin dvc.yaml >$out_file" w]
        } else {
            set out_fh [open $out_file w]
        }
    } elseif {$format} {
        set out_fh [open "|dprint fmt --stdin dvc.yaml" w]
    } else {
        set out_fh stdout
    }
    ::dvc::make_yaml $out_fh
    if {$out_fh ne "stdout"} {
        close $out_fh
    }
}
