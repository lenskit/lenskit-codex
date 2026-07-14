#!/usr/bin/env -S guarsh -U
#USAGE flag "-v --verbose" help="Output debug log messages."
#USAGE flag "--format" help="Format piepline output."
#USAGE flag "-o --output <file>" help="Write output to <file>."
#USAGE arg "<script...>" help="Render scripts specified by <script>."

package require logging
package require dvc

set format $usage(format)
if {[exists -var usage(output)]} {
    set out_file $usage(output)
}

foreach script $usage(script) {
    msg "evaluating pipeline $script"
    ::dvc::reset
    ::dvc::eval_pipeline $script
    set pid 0
    if {[exists out_file]} {
        msg "saving to $out_file"
        if {$format} {
            msg -debug "saving with dprint"
            set out_fh [open "|yamlfmt -in >$out_file" w]
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
