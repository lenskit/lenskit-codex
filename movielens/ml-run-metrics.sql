DROP VIEW IF EXISTS variants;
CREATE VIEW variants AS
SELECT
    fileno,
    regexp_extract(filename, '^runs/(\w+)-[\w-]+/', 1) AS split,
    regexp_extract(filename, '^runs/\w+-[\w-]+/([a-zA-Z0-9-]+)\.duckdb', 1) AS model,
    regexp_extract(filename, '^runs/\w+-([\w-]+)/', 1) AS config,
FROM run_files;
