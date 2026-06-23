# define the data import and preparation stages

stage import {
    cmd lenskit data convert --movielens $ml_fn.zip dataset
    dep $ml_fn.zip
    out dataset
}

stage stats {
    cmd lenskit codex sql -D ds_name=$ml_name -f ../ml-stats.sql stats.duckdb
    dep ../ml-stats.sql
    dep dataset
    out stats.duckdb
}

if {$ml_split eq "random"} {
    stage split-random {
        cmd lenskit codex split random.toml
        wdir splits
        # TODO: re-add random seed dependency
        dep random.toml
        dep ../dataset
        out random.parquet
    }
}
