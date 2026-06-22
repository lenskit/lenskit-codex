#!/usr/bin/env tclsh

namespace eval ::dvc {
    variable script ""
    variable stages {}
    variable cur_name ""
    variable cur_stage {}

    proc run_pipeline {src} {
        variable script
        set script $src

        puts stderr "running $script"
        namespace eval ::dvc::root source $script
    }

    proc lc_prefix {{name ""}} {
        variable cur_name
        variable script
        if {$name eq ""} {
            set name $cur_name
        }

        set loc "$script:"
        if {$name ne ""} {
            append loc "$name:"
        }
    }

    proc render_pipeline {{fh stdout}} {
        variable stages
        puts $fh "stages:"
        foreach {name stage} $stages {
            puts $fh "  $name:"
            puts $fh "    cmd: [dict get $stage cmd]"
            if {[dict exists $stage wdir]} {
                puts $fh "    wdir: [dict get $stage wdir]"
            }
            if {[dict exists $stage deps]} {
                puts $fh "    deps:"
                foreach dep [dict get $stage deps] {
                    puts $fh "    - $dep"
                }
            }
            if {[dict exists $stage outs]} {
                puts $fh "    outs:"
                foreach out [dict get $stage outs] {
                    lassign $out tracker file
                    switch $tracker {
                        git {
                            puts $fh "    - $file:"
                            puts $fh "        cache: false"
                        }
                        dvc {
                            puts $fh "    - $file"
                        }
                        default {
                            error "unknown tracker $tracker"
                        }
                    }
                }
            }
            if {[dict exists $stage metrics]} {
                puts $fh "    metrics:"
                foreach out [dict get $stage metrics] {
                    lassign $out tracker file
                    switch $tracker {
                        git {
                            puts $fh "    - $file:"
                            puts $fh "        cache: false"
                        }
                        dvc {
                            puts $fh "    - $file"
                        }
                        default {
                            error "unknown tracker $tracker"
                        }
                    }
                }
            }
        }
    }
}

namespace eval ::dvc::root {
    proc _require_stage {cmd} {
        if {$::dvc::cur_name eq ""} {
            error "[::dvc::lc_prefix] command $cmd only valid in a stage"
        }
    }

    # add a new stage to the active pipeline
    proc stage {name body} {
        if {$::dvc::cur_name ne ""} {
            error "[::dvc::lc_prefix $name] stage $cur_name is active, do you have nested stages?"
        }
        if {[dict exists stages $name]} {
            error "[::dvc::lc_prefix $name] stage already defined"
        }

        set ::dvc::cur_name $name
        set ::dvc::cur_stage {}

        uplevel $body

        if {![dict exists $::dvc::cur_stage cmd]} {
            error "[::dvc::lc_prefix] stage has no command"
        }

        lappend ::dvc::stages $name $::dvc::cur_stage
    }

    proc cmd {args} {
        _require_stage cmd
        dict append ::dvc::cur_stage cmd $args
    }

    proc wdir {args} {
        _require_stage wdir
        dict append ::dvc::cur_stage wdir $args
    }

    proc dep {args} {
        _require_stage dep
        dict lappend ::dvc::cur_stage deps {*}$args
    }

    proc out {args} {
        _require_stage out
        set done 0
        set tracker dvc
        set dest outs
        while {!$done && [llength $args]} {
            set arg [lindex $args 0]
            switch -glob -- $arg {
                -- {
                    set done 1
                    set args [lrange $args 1 end]
                }
                -nocache {
                    set tracker git
                    set args [lrange $args 1 end]
                }
                -metric {
                    set dest metrics
                    set args [lrange $args 1 end]
                }
                -* {
                    error "[::dvc::lc_prefix] unrecognized output option $arg"
                }
                default {
                    set done 1
                }
            }
        }

        foreach file $args {
            dict lappend ::dvc::cur_stage $dest [list $tracker $file]
        }
    }
}

set script [lindex $argv 0]

::dvc::run_pipeline $script

::dvc::render_pipeline
