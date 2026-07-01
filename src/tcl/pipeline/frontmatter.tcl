package provide frontmatter 0.1
package require logging

proc {doc load-meta} {path} {
    msg -debug "opening $path"
    set fh [open $path r]
    set header ""
    if {[gets $fh line] < 0} {
        msg -error "$path is empty"
        return {}
    }
    if {![regexp {^---+} $line]} {
        msg -warn "$path does not begin with header"
        return {}
    }

    while {[gets $fh line] >= 0} {
        if {[regexp {^---+} $line]} {
            break
        }
        append header "$line\n"
    }

    return [parse yaml $header]
}

ensemble doc
