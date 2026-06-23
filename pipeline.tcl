package require oscmd
package require logging
package require kvlookup
package require path

set documents [exec python scripts/parse-to-tcl.py --all-headers 2>@stderr]
msg "loaded [dict size $documents] documents"

set names [lsort [dict keys $documents]]
foreach doc $names {
    set meta [dict get $documents $doc]
    # remove .qmd
    set page [file rootname $doc]
    set page_dir [file dirname $doc]
    msg -debug "render stage for $page"
    stage "page/$page" {
        cmd quarto render $doc
        dep _quarto.yml
        dep $doc
        foreach dep [kvlookup -default {} $meta deps] {
            dep [path resolve $page_dir $dep]
        }
        out _freeze/$page
    }
}
