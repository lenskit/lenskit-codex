package require models

set search_args [list]
set search_deps [list]
if {$movielens(split) eq "random"} {
    lappend search_args "--split=splits/$movielens(split).toml"
    lappend search_args "--test-part=0"
    lappend search_deps splits/random.parquet

} else {
    if {$movielens(split) eq "fixed"} {
        lappend search_args --split=splits/fixed
        lappend search_deps splits/fixed/valid
    } else {
        lappend search_args --split=splits/${movielens(split)}.toml
        lappend search_deps splits/${movielens(split)}.toml
    }
    lappend search_args --test-part=valid
}
if {[info exists movielens(search-points)]} {
    lappend search_args --sample-count=$movielens(search-points)
}

foreach mod [model list -enabled $movielens(name)] {
    set out_dir sweeps/$mod/optuna/$mod
    stage "sweep-$mod-$movielens(split)-optuna" {
        cmd lenskit codex tune {*}$search_args $mod $out_dir
        dep {*}$search_deps
        dep [path relative !/models/${mod}/search.toml]
        out $out_dir
        out -nocache $out_dir.json
        out -nocache $out_dir-pipeline.json
        if {![info exists movielens(search-points)]} {
            param -file [path relative !/config.toml] tuning.optuna.points
        }
    }
}
