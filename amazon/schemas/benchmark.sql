CREATE SEQUENCE iid_sequence START 1;
CREATE SEQUENCE uid_sequence START 1;
CREATE TABLE items (
    item_id INT PRIMARY KEY DEFAULT nextval('iid_sequence'),
    asin VARCHAR NOT NULL UNIQUE,
);
CREATE TABLE users (
    user_id INT PRIMARY KEY DEFAULT nextval('uid_sequence'),
    user_code VARCHAR NOT NULL UNIQUE,
);

CREATE TYPE partition AS ENUM ('train', 'valid', 'test');

CREATE TABLE ratings (
    part PARTITION NOT NULL,
    user_id INT NOT NULL,
    item_id INT NOT NULL,
    rating FLOAT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
);
