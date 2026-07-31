-- Legacy Risk-Control MySQL inventory.
-- Run only with an approved read-only account after taking a backup.
-- Review and redact output before sharing.

SET SESSION TRANSACTION READ ONLY;
START TRANSACTION READ ONLY;

SELECT
  CURRENT_USER() AS current_user,
  @@hostname AS database_host,
  @@version AS database_version,
  @@read_only AS server_read_only,
  @@super_read_only AS server_super_read_only;

SELECT
  TABLE_NAME,
  TABLE_TYPE,
  ENGINE,
  TABLE_ROWS,
  CREATE_TIME,
  UPDATE_TIME,
  TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'risk_control'
ORDER BY TABLE_NAME;

SELECT
  TABLE_NAME,
  ORDINAL_POSITION,
  COLUMN_NAME,
  COLUMN_TYPE,
  IS_NULLABLE,
  COLUMN_DEFAULT,
  EXTRA
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'risk_control'
ORDER BY TABLE_NAME, ORDINAL_POSITION;

SELECT
  TABLE_NAME,
  INDEX_NAME,
  SEQ_IN_INDEX,
  COLUMN_NAME,
  NON_UNIQUE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'risk_control'
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

SELECT
  CONSTRAINT_NAME,
  TABLE_NAME,
  CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'risk_control'
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

SELECT
  'users' AS table_name,
  COUNT(*) AS row_count,
  SUM(password_hash IS NOT NULL AND password_hash <> '') AS password_hash_rows,
  MAX(updated_at) AS latest_update
FROM risk_control.users;

SELECT
  'user_sessions' AS table_name,
  COUNT(*) AS row_count,
  MAX(created_at) AS latest_create,
  MAX(expires_at) AS latest_expiry
FROM risk_control.user_sessions;

SELECT
  'accounts' AS table_name,
  COUNT(*) AS row_count,
  SUM(api_key_encrypted IS NOT NULL AND api_key_encrypted <> '') AS api_key_rows,
  SUM(api_secret_encrypted IS NOT NULL AND api_secret_encrypted <> '') AS api_secret_rows,
  MAX(updated_at) AS latest_update
FROM risk_control.accounts;

SELECT
  'assets' AS table_name,
  COUNT(*) AS row_count,
  SUM(bybit_positions IS NOT NULL) AS position_snapshot_rows,
  MAX(updated_at) AS latest_update
FROM risk_control.assets;

COMMIT;
