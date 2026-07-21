#USAGE flag "-v --verbose" help="Enable verbose logging."

package require logging
package require oscmd

set files [glob run-log/db/*.ndjson.zst]
msg "scanning [llength $files] DB files"

cd scratch/runlog-db

foreach file $files {
    msg "scanning $file"
    set fh [open "|zstd -dc ../../$file" r]
    while {[gets $fh line] >= 0} {
        set record [td parse json $line]
        set id [td get -native $record task_id]
        set d1 [string range $id 0 1]
        set d2 [string range $id 2 3]
        set dir $d1/$d2
        set path $dir/$id.json
        if {![file exists $path]} {
            msg -debug "saving task $id"
            file mkdir $dir
            td dump json -file $d1/$d2/$id.json $record
            oscmd run git add $d1/$d2/$id.json
            oscmd run git commit -m "add $id"
        } else {
            msg -debug "task $id already saved"
        }
    }
    close $fh
}
