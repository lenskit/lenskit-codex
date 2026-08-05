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

foreach mod [model list -implicit -enabled Steam-AU] {
    set out_dir searches/random/optuna/$mod

    if {[model searchable $mod]} {
        stage "search-$mod-random-optuna" {
            cmd lenskit codex tune --split=splits/random.toml --test-part=tune $mod $out_dir
            dep splits/random/train.dataset
            dep splits/random/tune.parquet
            dep [path relative !/models/${mod}/pipeline.toml]
            dep [path relative !/models/${mod}/search.toml]
            param -file [path relative !/lenskit.toml] tuning.defaults
            out $out_dir
            out -nocache $out_dir.json
            out -nocache $out_dir-pipeline.json
            param -file [path relative !/codex.toml] tuning.optuna.points
        }
    }
}

run begin-set Steam-AU random
foreach mod [model list -implicit -enabled Steam-AU] {
    run default $mod
    if {[model searchable $mod]} {
        run tuned $mod
    }
}
run collect
run save-manifest
