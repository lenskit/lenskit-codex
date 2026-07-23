#!/usr/bin/env -S guarsh -U
#USAGE flag "-v --verbose" help="Output debug log messages."
#USAGE flag "--format" help="Format piepline output."
#USAGE flag "-o --output <file>" help="Write output to <file>."
#USAGE arg "<script...>" help="Render scripts specified by <script>."

package require logging
package require dvc

set ::dvc::format_yaml $usage(format)
if {[exists -var usage(output)]} {
    set out_file $usage(output)
} else {
    set out_file -
}

foreach script $usage(script) {
    msg "evaluating pipeline $script"
    ::dvc::reset
    ::dvc::eval_pipeline $script
    ::dvc::save_yaml $out_file
}
