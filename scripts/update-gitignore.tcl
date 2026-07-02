#!/usr/bin/env tclsh
package require missing
package require logging
package require path

set ignore_lists [dict create]
set ignore_sets [dict create]

set ignore_files [exec find . -name .gitignore]
set yaml_files [exec find . -name dvc.yaml]

set ignore_count 0
foreach file $ignore_files {
    if {[string match ./.* $file]} {
        msg -debug "skipping $file"
        continue
    }
    msg "found ignore $file"
    set dir [path project [path create [file dirname $file]]]
    msg -debug "ignore dir: $dir"
    set fh [open $file r]
    while {[gets $fh line] >= 0} {
        set line [string trim $line]
        dict lappend ignore_lists $dir $line
        if {![string match #* $line]} {
            dict set ignore_sets $dir $line 1
            incr ignore_count
        }
    }
    close $fh
}

msg "found $ignore_count ignores in [array size ignore_lists] files"
foreach file $yaml_files {
    if {[string match ./.* $file]} {
        msg -debug "skipping $file"
        continue
    }
    msg "found pipeline $file"
    set dir [file dirname $file]
    set pipe [parse yaml -file $file]
    set stages [dict get $pipe stages]
    msg -debug "scanning [llength $stages] stages"
    foreach {name stage} $stages {
        msg -debug "scanning stage $stage"
        set sdir $dir
        if {[dict exists $stage wdir]} {
            set sdir [file join $sdir [dict get $stage wdir]]
        }
        set outs {}
        if {[dict exists $stage outs]} {
            lappend outs {*}[dict get $stage outs]
        }
        if {[dict exists $stage metrics]} {
            lappend metrics {*}[dict get $stage metrics]
        }
        foreach out $outs {
            set out [string trim $out]
            if {[llength $out] == 2} {
                continue
            }
            set path [path project [path create $sdir $out]]
            set odir [file dirname $path]
            set oname [file tail $path]
            if {![dict exists $ignore_sets $odir "/$oname"]} {
                dict lappend ignore_lists $odir "/$oname"
                dict set ignore_sets $odir "/$oname" 1
            }
        }
    }
}

foreach {dir ignores} $ignore_lists {
    msg "$dir has [llength $ignores] ignore lines"
    if {![file exists $dir]} {
        msg "creating $dir"
        file mkdir $dir
    }
    set fh [open "$dir/.gitignore" w]
    foreach line $ignores {
        puts $fh $line
    }
    close $fh
}
