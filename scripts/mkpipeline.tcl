#!/usr/bin/env tclsh

package require logging
package require dvc
package require getopt

set scripts {}

getopt arg $argv {
    -v - --verbose {
        # increase logging verbosity
        logging::configure -verbose
    }

    arglist {
        set scripts $arg
    }
}

foreach script $scripts {
    msg "evaluating pipeline $script"
    ::dvc::reset
    ::dvc::eval_pipeline $script
    ::dvc::make_yaml
}
