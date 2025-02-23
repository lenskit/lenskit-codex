CREATE VIEW item_ids AS
SELECT file_row_number - 1 AS item_num, item_id
FROM read_parquet(project_path(['movielens', '$ds_name', 'dataset', 'item.parquet']), file_row_number=TRUE);

CREATE VIEW user_ids AS
SELECT file_row_number - 1 AS user_num, user_id
FROM read_parquet(project_path(['movielens', '$ds_name', 'dataset', 'user.parquet']), file_row_number=TRUE);

CREATE VIEW ratings AS
SELECT user_id, item_id, rating, timestamp
FROM read_parquet(project_path(['movielens', '$ds_name', 'dataset', 'rating.parquet']))
JOIN item_ids USING (item_num)
JOIN user_ids USING (user_num);

SELECT * FROM ratings LIMIT 10;

CREATE TABLE global_stats AS
SELECT COUNT(*) AS n_ratings,
    COUNT(DISTINCT user_id) AS n_users,
    COUNT(DISTINCT item_id) AS n_items,
    MIN(timestamp) AS first_rating,
    MAX(timestamp) AS last_rating
FROM ratings;

CREATE TABLE item_stats AS
SELECT item_id,
    COUNT(*) AS n_ratings,
    AVG(rating) AS mean_rating,
    ROW_NUMBER() OVER (ORDER BY n_ratings) AS int_rank,
    PERCENT_RANK() OVER (ORDER BY n_ratings) AS rank,
FROM ratings
GROUP BY item_id
ORDER BY n_ratings;

CREATE TABLE user_stats AS
SELECT user_id,
    COUNT(*) AS n_ratings,
    AVG(rating) AS mean_rating,
    MIN(timestamp) AS first_rating,
    MAX(timestamp) AS last_rating,
FROM ratings
GROUP BY user_id
ORDER BY n_ratings;

CREATE TABLE year_stats AS
SELECT year(timestamp) AS year,
    count(*) AS n_ratings,
    count(distinct user_id) AS n_users,
    count(distinct item_id) AS n_items,
    avg(rating) AS mean_rating
FROM ratings
GROUP BY year(timestamp)
ORDER BY year;

CREATE TABLE month_stats AS
SELECT year(timestamp) AS year, month(timestamp) AS month,
    year + (month - 1) / 12 AS fracyear,
    count(*) AS n_ratings,
    count(distinct user_id) AS n_users,
    count(distinct item_id) AS n_items,
    avg(rating) AS mean_rating
FROM ratings
GROUP BY year(timestamp), month(timestamp)
ORDER BY year, month;
