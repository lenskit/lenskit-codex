package require models
package require runs

set _dt toml
if {$ml_split eq "random"} {
    set _dt parquet
}

# start emitting stages for runs - with the name and the split
run begin-set $ml_name $ml_split

foreach mod [model list] {
    run default $mod
    # if {[model searchable $mod]} {
    #     run tuned $mod
    # }
}
run collect
run save-manifest
