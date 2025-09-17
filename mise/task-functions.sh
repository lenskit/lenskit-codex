VERBOSE="${VERBOSE:-0}"

dbg() {
    if (($VERBOSE)); then
        echo "$@" >&2
    fi
}

msg() {
    echo "$@" >&2
}

runx() {
    echo "+ $*" >&2
    "$@"
    return "$?"
}
