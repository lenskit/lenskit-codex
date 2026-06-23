# Path libraries for the pipeline
package provide path 0.1
package require missing

namespace eval ::path {
    # get the project root directory
    proc root {} {
        if {[info exists env(PROJECT_ROOT)]} {
            return [file normalize $env(PROJECT_ROOT)]
        }

        set path [file normalize [pwd]]
        while {![file exists [file join $path pyproject.toml]]} {
            set p2 [file dirname $path]
            if {$p2 eq $path} {
                error "cannot find project root"
            }
            set path $p2
        }
        return $path
    }

    # Resolve a complete, project-relative path
    proc resolve {args} {
        set root [root]
        set path [file join $root {*}$args]
        set path [file normalize $path]
        if {![string match $root* $path]} {
            error "resolved path $path not inside project root"
        }
        return [relative $root $path]
    }

    # Obtain a path relative to another path
    proc relative {base path} {
        set bps [file split $base]
        set tps [file split $path]
        while {[llength $bps]} {
            set bp [lshift bps]
            set tp [lshift tps]
            if {$bp ne $tp} {
                error "target path $path not within $base"
            }
        }
        return [join $tps /]
    }

    namespace export root resolve relative
    namespace ensemble create
}
