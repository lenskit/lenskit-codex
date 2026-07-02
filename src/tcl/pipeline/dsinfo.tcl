# Support for dataset info manifests.
package provide dsinfo 0.1
package require logging

proc {dsinfo save} {info {file dataset.json}} {
    set json [::json::encode $info {
        obj
        name str
        models {list str}
        splits {list str}
        searches {list str}
    }]
    msg "saving manifest for [dict get $info name] to $file"
    set fh [open $file w]
    puts $fh $json
    close $fh
}

ensemble dsinfo
