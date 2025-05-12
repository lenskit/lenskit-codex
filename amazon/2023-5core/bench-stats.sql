SET enable_progress_bar = TRUE;

CREATE TYPE partition AS ENUM ('train', 'valid', 'test');
CREATE TYPE category AS ENUM (SELECT DISTINCT regexp_extract(file, '(\w+)\.\w+\.csv.gz', 1) FROM glob('data/*.csv.gz'));

CREATE TEMPORARY VIEW raw_ratings AS
SELECT
    CAST(regexp_extract(filename, '(\w+)\.\w+\.csv.gz', 1) AS category) AS category,
    CAST(regexp_extract(filename, '\w+\.(\w+)\.csv.gz', 1) AS partition) AS part,
    user_id, parent_asin AS item_id, cast(rating AS FLOAT) AS rating, epoch_ms(timestamp) AS timestamp
FROM read_csv('data/*.csv.gz', filename=TRUE);

SELECT log_msg('computing file statistics');
CREATE TABLE file_stats AS
SELECT category, part,
    COUNT(*) AS n_ratings,
    COUNT(DISTINCT user_id) AS n_users,
    COUNT(DISTINCT item_id) AS n_items,
    MIN(timestamp) AS first_rating,
    MAX(timestamp) AS last_rating,
FROM raw_ratings
GROUP BY category, part;

SELECT log_msg('computing item statistics');
CREATE TABLE item_stats AS
SELECT item_id, category, part,
    COUNT(*) AS n_ratings,
    AVG(rating) AS mean_rating,
    ROW_NUMBER() OVER (ORDER BY n_ratings) AS int_rank,
    PERCENT_RANK() OVER (ORDER BY n_ratings) AS rank,
FROM raw_ratings
GROUP BY item_id, category, part
ORDER BY category, part, n_ratings;

SELECT log_msg('computing user statistics');
CREATE TABLE user_stats AS
SELECT user_id, category, part,
    COUNT(*) AS n_ratings,
    AVG(rating) AS mean_rating,
    MIN(timestamp) AS first_rating,
    MAX(timestamp) AS last_rating,
FROM raw_ratings
GROUP BY user_id, category, part
ORDER BY category, part, n_ratings;

SELECT log_msg('computing year statistics');
CREATE TABLE year_stats AS
SELECT category, year(timestamp) AS year,
    count(*) AS n_ratings,
    count(distinct user_id) AS n_users,
    count(distinct item_id) AS n_items,
    avg(rating) AS mean_rating
FROM raw_ratings
WHERE part = 'train'
GROUP BY category, year(timestamp)
ORDER BY year;

SELECT log_msg('computing month statistics');
CREATE TABLE month_stats AS
SELECT category, year(timestamp) AS year, month(timestamp) AS month,
    year + (month - 1) / 12 AS fracyear,
    count(*) AS n_ratings,
    count(distinct user_id) AS n_users,
    count(distinct item_id) AS n_items,
    avg(rating) AS mean_rating
FROM raw_ratings
WHERE part = 'train'
GROUP BY category, year(timestamp), month(timestamp)
ORDER BY year, month;
