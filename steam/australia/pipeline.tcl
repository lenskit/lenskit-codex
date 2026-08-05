package require models
package require runs

stage import-interactions {
    cmd lenskit data convert --steam ../data/australian_users_items.json.gz dataset
    dep ../data/australian_users_items.json.gz
    out dataset
}

stage split-interactions {
    cmd lenskit codex split splits/random.toml
    param -file !/lenskit.toml random.seed
    dep splits/random.toml
    dep dataset
    out splits/random
}

run begin-set Steam-AU random
foreach mod [model list -implicit -enabled Steam-AU] {
    run default $mod
}
run collect
run save-manifest
