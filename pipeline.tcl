package require oscmd
package require logging
package require kvlookup
package require path
package require frontmatter

msg -debug "scanning for Quarto documents"
set doc_files [exec fd -g *.qmd -E _*]
msg "reading front-matter from [llength $doc_files]"

set documents {}
foreach doc $doc_files {
    msg -debug "loading frontmatter from $doc"
    set header [doc load-meta $doc]
    dict set documents $doc $header
}

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
            dep [path project [path create $page_dir $dep]]
        }
        out _freeze/$page
    }
}
