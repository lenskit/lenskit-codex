set foo bar

stage test {
    cmd cat $foo
    wdir soup
    dep wombat.csv
    out wombat.parquet
    out -nocache wombat-stats.json
}
