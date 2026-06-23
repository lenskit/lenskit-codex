source defs.tcl

stage aggregate-rating-stats {
    cmd lenskit codex movielens aggregate -d merged-stats.duckdb {*}$ML_VERSIONS
    foreach ver $ML_VERSIONS {
        dep $ver/stats.duckdb
    }
    out merged-stats.duckdb
}
