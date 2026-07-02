# Path libraries for the pipeline
package provide path 0.2
package require missing
package require logging

namespace eval ::path {
    variable working_dir "!!UNDEF"

    # get the absolute path to the project root
    proc project-root {} {
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

    # get the type of a path: absolute, relative, project
    proc type {path} {
        if {[string match /* $path]} {
            return "absolute"
        } elseif {[string match !/* $path]} {
            return "project"
        } else {
            return "relative"
        }
    }

    # Get the current directory
    proc current {} {
        variable working_dir
        if {$working_dir eq "!!UNDEF"} {
            return [pwd]
        } else {
            return $working_dir
        }
    }

    # Run a command with a different working directory
    proc inside {path body} {
        variable working_dir
        set old $working_dir
        set working_dir [path absolute $path]
        msg -debug "logically entering $working_dir"
        uplevel $body
        msg -debug "logically leaving $working_dir"
        set working_dir old
    }

    # Create a path string, combining parts.
    proc create {args} {
        if {[lpeek $args] eq "-project"} {
            lshift args
            lunshift args !
        }

        set segments [list]
        foreach seg $args {
            if {[type $seg] eq "relative"} {
                lappend segments $seg
            } else {
                set segments $seg
            }
        }
        return [cleanup [join $args /]]
    }

    proc cleanup {path} {
        set parts [lreverse [file split $path]]
        set out [list]
        while {![lempty $parts]} {
            set part [lpop parts]
            if {$part eq "/"} {
                if {[lempty $out]} {
                    lappend out ""
                }
            } elseif {$part eq ".."} {
                if {[lindex $out end] eq "!"} {
                    error "$path: relative segment goes above project root"
                } elseif {[lempty $out]} {
                    lappend out ..
                } else {
                    lpop out
                }
            } elseif {$part eq "."} {
                # skip
            } else {
                lappend out $part
            }
        }
        return [join $out /]
    }

    # get a project-relative path
    proc project {path} {
        # project-relative path: use as-is
        if {[string match !/* $path]} {
            return [string range $path 2 end]
        }
        set path [create [current] $path]
        set root [project-root]
        set rel [relativize $root $path]
        if {[string match ../* $rel]} {
            error "$path is outside project root"
        }
        return $rel
    }

    # get a current-relative path
    proc relative {path} {
        switch [type $path] {
            relative {
                return $path
            }
            project {
                set path [file join [project-root] [string range $path 2 end]]
            }
        }

        set cwd [current]
        return [relativize $cwd $path]
    }

    # get an absolute path
    proc absolute {path} {
        switch [type $path] {
            relative {
                return [file join [current] $path]
            }
            project {
                return [file join [project-root] [string range $path 2 end]]
            }
            absolute {
                return $path
            }
        }
    }

    # resolve a path to a usable path
    proc resolve {path} {
        return [absolute $path]
    }

    # Convert an absolute path into a relative one.
    proc relativize {base path} {
        set bps [file split $base]
        set tps [file split $path]
        # eat common components
        while {![lempty $bps] && [lpeek $bps] eq [lpeek $tps]} {
            set bp [lshift bps]
            set tp [lshift tps]
        }
        # append .. as needed
        while {![lempty $bps]} {
            lunshift tps ..
            lshift bps
        }
        return [join $tps /]
    }

    namespace export project-root type create cleanup project relative absolute resolve
    namespace ensemble create
}
