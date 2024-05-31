CREATE VIEW item_stats AS
SELECT item_id,
    COUNT(*) AS n_ratings,
    AVG(rating) AS mean_rating,
    ROW_NUMBER() OVER (ORDER BY n_ratings) AS int_rank,
    PERCENT_RANK() OVER (ORDER BY n_ratings) AS rank,
FROM ratings
GROUP BY item_id
ORDER BY n_ratings;

CREATE VIEW user_stats AS
SELECT user_id,
    COUNT(*) AS n_ratings,
    AVG(rating) AS mean_rating,
    MIN(timestamp) AS first_rating,
    MAX(timestamp) AS last_rating,
FROM ratings
GROUP BY user_id
ORDER BY n_ratings;

CREATE VIEW year_stats AS
SELECT year(timestamp) AS year,
    count(*) AS n_ratings,
    count(distinct user_id) AS n_users,
    count(distinct item_id) AS n_items,
    avg(rating) AS mean_rating
FROM ratings
GROUP BY year(timestamp)
ORDER BY year;

CREATE VIEW month_stats AS
SELECT year(timestamp) AS year, month(timestamp) AS month,
    year + (month - 1) / 12 AS fracyear,
    count(*) AS n_ratings,
    count(distinct user_id) AS n_users,
    count(distinct item_id) AS n_items,
    avg(rating) AS mean_rating
FROM ratings
GROUP BY year(timestamp), month(timestamp)
ORDER BY year, month;
