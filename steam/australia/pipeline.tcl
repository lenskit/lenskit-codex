stage import-interactions {
    cmd lenskit data convert --steam ../data/australian_users_items.json.gz dataset
    dep ../data/australian_users_items.json.gz
    out dataset
}
