package provide nestout 0.1

namespace eval nest {
    variable out
    variable depth 0

    proc open {fh} {
        variable out
        set out $fh
    }

    proc push {{n 1}} {
        variable depth
        incr depth $n
    }

    proc pop {{n 1}} {
        variable depth
        incr depth -$n
    }

    proc puts {str} {
        variable out
        variable depth
        set line [string repeat " " [expr {$depth * 2}]]
        append line $str
        ::puts $out $line
    }

    proc close {} {
        variable out
        variable depth
        set out {}
        set depth 0
    }

    namespace export open push pop puts
    namespace ensemble create
}
