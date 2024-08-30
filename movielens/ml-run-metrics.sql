DROP VIEW IF EXISTS metrics;
CREATE VIEW metrics AS
SELECT
    regexp_extract(file, '^runs/(\w+)-[\w-]+/', 1) AS split,
    regexp_extract(file, '^runs/\w+-[\w-]+/([a-zA-Z0-9-]+)\.duckdb', 1) AS model,
    regexp_extract(file, '^runs/\w+-([\w-]+)/', 1) AS config,
    run, ndcg, mrr, user_rmse
FROM run_metrics;
