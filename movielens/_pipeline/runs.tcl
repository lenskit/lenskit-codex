package require models
package require runs

set _dt toml
if {$movielens(split) eq "random"} {
    set _dt parquet
}

# start emitting stages for runs - with the name and the split
run begin-set $movielens(name) $movielens(split)

# now we emit a runs for each model
foreach mod [model list -enabled $movielens(name)] {
    run default $mod
    # if {[model searchable $mod]} {
    #     run tuned $mod
    # }
}
run collect
run save-manifest
