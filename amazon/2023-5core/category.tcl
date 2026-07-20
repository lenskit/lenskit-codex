package require missing
package require logging

proc azcat args {
    set tune yes
    set sample 0
    if {[exists -var ::valid_sample_size]} {
        set sample $::valid_sample_size
    }

    while {![lempty $args]} {
        set arg [lpeek $args]
        switch -glob -- $arg {
            -no-tune {
                set tune no
                lshift args
            }
            -sample-valid {
                lshift args
                set sample [lshift args]
            }
            -- {
                lshift args
                break
            }
            -* {
                error "unrecognized option $arg"
            }
            default {
                break
            }
        }
    }

    if {[llength $args] != 2} {
        error "invalid arguments"
    }
    lassign $args cat full

    set ds "AZ-2023-5core-$cat"
    msg "rendering Amazon 2023 category $cat ($full)"
    subdir $cat {
        stage import-valid-train {
            set src ../data/$full.train.csv.gz
            cmd lenskit data convert --amazon $src splits/fixed/valid/train.dataset
            dep $src
            out splits/fixed/valid/train.dataset
        }

        stage import-valid-test {
            set src ../data/$full.valid.csv.gz
            if {$sample} {
                set dst splits/fixed/valid/test.full.parquet
            } else {
                set dst splits/fixed/valid/test.parquet
            }
            cmd lenskit data convert --amazon --item-lists $src $dst
            dep $src
            out $dst
        }
        if {$sample} {
            stage subset-valid-test {
                cmd lenskit data subset --sample-rows=$sample --item-lists splits/fixed/valid/test.full.parquet splits/fixed/valid/test.parquet
                dep splits/fixed/valid/test.full.parquet
                out splits/fixed/valid/test.parquet
            }
        }

        stage import-test-train {
            set train ../data/$full.train.csv.gz
            set valid ../data/$full.valid.csv.gz
            cmd lenskit data convert --amazon $train $valid splits/fixed/valid/train.dataset
            dep $train $valid
            out splits/fixed/test/train.dataset
        }
        stage import-test-test {
            set src ../data/$full.test.csv.gz
            cmd lenskit data convert --amazon --item-lists $src splits/fixed/test/test.parquet
            dep $src
            out splits/fixed/test/test.parquet
        }

        run begin-set $ds fixed
        foreach mod [model list -enabled $ds] {
            run default $mod
        }
        run collect
        run save-manifest

        stage export-trec-qrels-valid {
            cmd lenskit codex trec export qrels -o splits/fixed/valid.qrels.gz splits/fixed/test/test.parquet
            dep splits/fixed/valid/test.parquet
            out splits/fixed/valid.qrels.gz
        }
        stage export-trec-qrels-test {
            cmd lenskit codex trec export qrels -o splits/fixed/test.qrels.gz splits/fixed/test/test.parquet
            dep splits/fixed/test/test.parquet
            out splits/fixed/test.qrels.gz
        }
        stage export-trec-default-runs {
            cmd lenskit codex trec export runs -o runs/fixed/default.run.gz runs/fixed/*-default
            out runs/fixed.default.run.gz
            foreach mod [model list] {
                if {[model enabled $mod $ds]} {
                    dep runs/fixed/$mod-default/recommendations.parquet
                }
            }
        }
    }
}
