package provide parse 0.1
package require path

namespace eval ::parse {
    proc toml {file} {
        set proc [path resolve -project scripts/parse-to-tcl.py]
        set result [exec python $proc -v -f toml $file 2>@stderr]
        return $result
    }

    namespace export toml
    namespace ensemble create
}
