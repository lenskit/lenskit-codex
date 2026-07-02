set movielens {
    name ML100K
    filename ml-100k
    split random
    search yes
    search-points 50
}

source ../_pipeline/ml-version.tcl
