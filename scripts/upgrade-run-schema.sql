--#segment err=continue
ALTER TABLE train_metrics RENAME TO train_stats;

--#segment err=continue
ALTER TABLE run_specs RENAME COLUMN rec_idx TO run;

--#segment err=continue
ALTER TABLE train_stats RENAME COLUMN rec_idx TO run;
ALTER TABLE user_metrics RENAME COLUMN rec_idx TO run;
ALTER TABLE user_metrics RENAME COLUMN user TO user_id;
ALTER TABLE recommendations RENAME COLUMN rec_idx TO run;
ALTER TABLE recommendations RENAME COLUMN user TO user_id;
ALTER TABLE recommendations RENAME COLUMN item TO item_id;

--#segment err=continue
ALTER TABLE predictions RENAME COLUMN rec_idx TO run;
ALTER TABLE predictions RENAME COLUMN user TO user_id;
ALTER TABLE predictions RENAME COLUMN item TO item_id;
