package mysqlrepo

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"data-service/internal/config"
	"data-service/internal/model"
)

type Repository struct {
	db *sql.DB
}

type rawPoint struct {
	accountID      int64
	totalAsset     float64
	availableFund  float64
	updatedAt      time.Time
	initialCapital float64
}

func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}

func (r *Repository) EnsureSchema(ctx context.Context) error {
	statements := []string{
		`CREATE TABLE IF NOT EXISTS users (
			id BIGINT AUTO_INCREMENT PRIMARY KEY,
			username VARCHAR(50) NOT NULL UNIQUE,
			password_hash VARCHAR(255) NOT NULL,
			email VARCHAR(100) NULL,
			role ENUM('guest','employee','admin') NOT NULL DEFAULT 'guest',
			department VARCHAR(100) NULL,
			managed_strategies JSON NULL,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`,
		`CREATE TABLE IF NOT EXISTS accounts (
			id BIGINT AUTO_INCREMENT PRIMARY KEY,
			name VARCHAR(100) NOT NULL,
			account_type ENUM('puridia','mt5_exam','bybit','trader_a','trader_b') NOT NULL,
			account_address VARCHAR(255) NOT NULL,
			initial_capital DECIMAL(20,8) NOT NULL,
			parent_id BIGINT NULL,
			arbitrary_flag TINYINT(1) NOT NULL DEFAULT 0,
			api_key_encrypted VARCHAR(500) NULL,
			api_secret_encrypted VARCHAR(500) NULL,
			owner_id BIGINT NULL,
			status ENUM('active','inactive') NOT NULL DEFAULT 'active',
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
			KEY owner_id (owner_id),
			CONSTRAINT accounts_ibfk_1 FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`,
		`CREATE TABLE IF NOT EXISTS assets (
			id BIGINT AUTO_INCREMENT PRIMARY KEY,
			account_id BIGINT NOT NULL,
			total_asset DECIMAL(20,8) NOT NULL,
			available_fund DECIMAL(20,8) NOT NULL,
			bybit_positions JSON NULL,
			update_frequency VARCHAR(20) NOT NULL DEFAULT '5m',
			data_source VARCHAR(50) NOT NULL DEFAULT 'system',
			snapshot_kind VARCHAR(20) NOT NULL DEFAULT 'valuation',
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
			KEY account_id (account_id),
			CONSTRAINT assets_ibfk_1 FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`,
	}
	for _, stmt := range statements {
		if _, err := r.db.ExecContext(ctx, stmt); err != nil {
			return err
		}
	}
	accountColumns := map[string]string{
		"api_key_encrypted":    "VARCHAR(500) NULL",
		"api_secret_encrypted": "VARCHAR(500) NULL",
	}
	for name, definition := range accountColumns {
		if err := r.addColumnIfMissing(ctx, "accounts", name, definition); err != nil {
			return err
		}
	}
	assetColumns := map[string]string{
		"snapshot_kind": "VARCHAR(20) NOT NULL DEFAULT 'valuation'",
	}
	for name, definition := range assetColumns {
		if err := r.addColumnIfMissing(ctx, "assets", name, definition); err != nil {
			return err
		}
	}
	_ = r.createIndex(ctx, "idx_accounts_type_address", "accounts", "account_type, account_address")
	_ = r.createIndex(ctx, "idx_assets_account_updated", "assets", "account_id, updated_at")
	_ = r.createIndex(ctx, "idx_assets_kind_account_updated", "assets", "snapshot_kind, account_id, updated_at")
	return nil
}

func (r *Repository) addColumnIfMissing(ctx context.Context, table, column, definition string) error {
	var exists int
	err := r.db.QueryRowContext(ctx, `
		SELECT COUNT(*)
		FROM information_schema.COLUMNS
		WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ? AND COLUMN_NAME = ?`,
		table,
		column,
	).Scan(&exists)
	if err != nil {
		return err
	}
	if exists > 0 {
		return nil
	}
	_, err = r.db.ExecContext(ctx, fmt.Sprintf("ALTER TABLE %s ADD COLUMN %s %s", table, column, definition))
	return err
}

func (r *Repository) createIndex(ctx context.Context, name, table, columns string) error {
	_, err := r.db.ExecContext(ctx, fmt.Sprintf("CREATE INDEX %s ON %s (%s)", name, table, columns))
	if err != nil && strings.Contains(strings.ToLower(err.Error()), "duplicate") {
		return nil
	}
	return err
}

func (r *Repository) EnsureBybitAccount(ctx context.Context, cfg config.BybitConfig, observedEquity float64) (*model.Account, error) {
	address := strings.TrimSpace(cfg.AccountAddress)
	if address == "" {
		address = "bybit-unified"
	}
	account, err := r.GetAccountByAddress(ctx, address, "bybit")
	if err != nil {
		return nil, err
	}
	if account != nil {
		if account.InitialCapital <= 0 && observedEquity > 0 {
			_, err := r.db.ExecContext(ctx, `UPDATE accounts SET initial_capital=? WHERE id=?`, observedEquity, account.ID)
			if err != nil {
				return nil, err
			}
			account.InitialCapital = observedEquity
		}
		return account, nil
	}

	initial := cfg.InitialCapital
	if initial <= 0 && observedEquity > 0 {
		initial = observedEquity
	}
	if initial <= 0 {
		initial = 1
	}
	name := strings.TrimSpace(cfg.AccountName)
	if name == "" {
		name = "Bybit Unified Account"
	}

	res, err := r.db.ExecContext(ctx, `INSERT INTO accounts
		(name, account_type, account_address, initial_capital, arbitrary_flag, status)
		VALUES (?, 'bybit', ?, ?, 0, 'active')`, name, address, initial)
	if err != nil {
		return nil, err
	}
	id, _ := res.LastInsertId()
	return r.GetAccountByID(ctx, id)
}

func (r *Repository) CreateAccount(ctx context.Context, account *model.Account) (*model.Account, error) {
	if account.InitialCapital <= 0 {
		account.InitialCapital = 1
	}
	if account.Status == "" {
		account.Status = "active"
	}
	res, err := r.db.ExecContext(ctx, `INSERT INTO accounts
		(name, account_type, account_address, initial_capital, parent_id, arbitrary_flag, api_key_encrypted, api_secret_encrypted, owner_id, status)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		account.Name,
		account.AccountType,
		account.AccountAddress,
		account.InitialCapital,
		account.ParentID,
		account.ArbitraryFlag,
		nullableString(account.APIKeyEncrypted),
		nullableString(account.APISecretEncrypted),
		account.OwnerID,
		account.Status,
	)
	if err != nil {
		return nil, err
	}
	id, _ := res.LastInsertId()
	return r.GetAccountByID(ctx, id)
}

func (r *Repository) DeleteAccount(ctx context.Context, id int64) error {
	res, err := r.db.ExecContext(ctx, `DELETE FROM accounts WHERE id=?`, id)
	if err != nil {
		return err
	}
	affected, _ := res.RowsAffected()
	if affected == 0 {
		return sql.ErrNoRows
	}
	return nil
}

func (r *Repository) InsertAssetSnapshot(ctx context.Context, accountID int64, balance *model.WalletBalance, snapshotKind string, updatedAt time.Time) error {
	snapshotKind = strings.TrimSpace(snapshotKind)
	if snapshotKind == "" {
		snapshotKind = "current"
	}
	if updatedAt.IsZero() {
		updatedAt = time.Now()
	}
	_, err := r.db.ExecContext(ctx, `INSERT INTO assets
		(account_id, total_asset, available_fund, bybit_positions, update_frequency, data_source, snapshot_kind, updated_at)
		VALUES (?, ?, ?, ?, '5m', 'bybit', ?, ?)`,
		accountID,
		balance.TotalEquity,
		balance.AvailableBalance,
		nullableJSON(balance.Raw),
		snapshotKind,
		updatedAt,
	)
	return err
}

func (r *Repository) ListAccounts(ctx context.Context) ([]model.Account, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT
			a.id, a.name, a.account_type, a.account_address, a.initial_capital,
			a.parent_id, a.arbitrary_flag, a.owner_id, a.status, a.created_at, a.updated_at,
			(a.api_key_encrypted IS NOT NULL AND a.api_key_encrypted <> ''),
			(a.api_secret_encrypted IS NOT NULL AND a.api_secret_encrypted <> ''),
			la.total_asset, la.available_fund, la.updated_at
		FROM accounts a
		LEFT JOIN assets la ON la.id = (
			SELECT id FROM assets WHERE account_id = a.id ORDER BY updated_at DESC, id DESC LIMIT 1
		)
		ORDER BY a.id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var accounts []model.Account
	for rows.Next() {
		account, err := scanAccountWithAsset(rows)
		if err != nil {
			return nil, err
		}
		accounts = append(accounts, account)
	}
	return accounts, rows.Err()
}

func (r *Repository) ListAccountsForSync(ctx context.Context) ([]model.Account, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT
			a.id, a.name, a.account_type, a.account_address, a.initial_capital,
			a.parent_id, a.arbitrary_flag, a.owner_id, a.status, a.created_at, a.updated_at,
			(a.api_key_encrypted IS NOT NULL AND a.api_key_encrypted <> ''),
			(a.api_secret_encrypted IS NOT NULL AND a.api_secret_encrypted <> ''),
			a.api_key_encrypted, a.api_secret_encrypted,
			la.total_asset, la.available_fund, la.updated_at
		FROM accounts a
		LEFT JOIN assets la ON la.id = (
			SELECT id FROM assets WHERE account_id = a.id ORDER BY updated_at DESC, id DESC LIMIT 1
		)
		WHERE a.status = 'active'
		ORDER BY a.id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var accounts []model.Account
	for rows.Next() {
		account, err := scanAccountWithAssetAndCredentials(rows)
		if err != nil {
			return nil, err
		}
		accounts = append(accounts, account)
	}
	return accounts, rows.Err()
}

func (r *Repository) GetAccountByID(ctx context.Context, id int64) (*model.Account, error) {
	row := r.db.QueryRowContext(ctx, `SELECT
			a.id, a.name, a.account_type, a.account_address, a.initial_capital,
			a.parent_id, a.arbitrary_flag, a.owner_id, a.status, a.created_at, a.updated_at,
			(a.api_key_encrypted IS NOT NULL AND a.api_key_encrypted <> ''),
			(a.api_secret_encrypted IS NOT NULL AND a.api_secret_encrypted <> ''),
			la.total_asset, la.available_fund, la.updated_at
		FROM accounts a
		LEFT JOIN assets la ON la.id = (
			SELECT id FROM assets WHERE account_id = a.id ORDER BY updated_at DESC, id DESC LIMIT 1
		)
		WHERE a.id = ?`, id)
	account, err := scanAccountWithAsset(row)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	return &account, err
}

func (r *Repository) GetAccountByAddress(ctx context.Context, address, accountType string) (*model.Account, error) {
	row := r.db.QueryRowContext(ctx, `SELECT
			a.id, a.name, a.account_type, a.account_address, a.initial_capital,
			a.parent_id, a.arbitrary_flag, a.owner_id, a.status, a.created_at, a.updated_at,
			(a.api_key_encrypted IS NOT NULL AND a.api_key_encrypted <> ''),
			(a.api_secret_encrypted IS NOT NULL AND a.api_secret_encrypted <> ''),
			la.total_asset, la.available_fund, la.updated_at
		FROM accounts a
		LEFT JOIN assets la ON la.id = (
			SELECT id FROM assets WHERE account_id = a.id ORDER BY updated_at DESC, id DESC LIMIT 1
		)
		WHERE a.account_address = ? AND a.account_type = ?
		ORDER BY a.id DESC LIMIT 1`, address, accountType)
	account, err := scanAccountWithAsset(row)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	return &account, err
}

func (r *Repository) TotalAssets(ctx context.Context) (float64, time.Time, error) {
	row := r.db.QueryRowContext(ctx, `SELECT
			COALESCE(SUM(la.total_asset), 0),
			MAX(la.updated_at)
		FROM accounts a
		LEFT JOIN assets la ON la.id = (
			SELECT id FROM assets WHERE account_id = a.id ORDER BY updated_at DESC, id DESC LIMIT 1
		)
		WHERE a.status = 'active'`)
	var total float64
	var updatedAt sql.NullTime
	if err := row.Scan(&total, &updatedAt); err != nil {
		return 0, time.Time{}, err
	}
	if !updatedAt.Valid {
		return total, time.Time{}, nil
	}
	return total, updatedAt.Time, nil
}

func (r *Repository) NetValueHistory(ctx context.Context, filter model.HistoryFilter) ([]model.NetValuePoint, error) {
	if filter.AccountID == 0 && filter.CheckCode != "" {
		accountType := normalizePlatform(filter.Platform)
		account, err := r.GetAccountByAddress(ctx, filter.CheckCode, accountType)
		if err != nil {
			return nil, err
		}
		if account == nil {
			return []model.NetValuePoint{}, nil
		}
		filter.AccountID = account.ID
	}
	if filter.Limit <= 0 {
		filter.Limit = 1000
	}
	if filter.Limit > 20000 {
		filter.Limit = 20000
	}

	where := []string{"a.status = 'active'", "s.snapshot_kind = 'valuation'"}
	args := []interface{}{}
	if filter.AccountID > 0 {
		where = append(where, "a.id = ?")
		args = append(args, filter.AccountID)
	}
	if filter.From != nil {
		where = append(where, "s.updated_at >= ?")
		args = append(args, *filter.From)
	}
	if filter.To != nil {
		where = append(where, "s.updated_at <= ?")
		args = append(args, *filter.To)
	}
	args = append(args, filter.Limit)

	query := fmt.Sprintf(`SELECT
			s.account_id, s.total_asset, s.available_fund, s.updated_at, a.initial_capital
		FROM assets s
		INNER JOIN accounts a ON a.id = s.account_id
		WHERE %s
		ORDER BY s.updated_at DESC, s.id DESC
		LIMIT ?`, strings.Join(where, " AND "))

	rows, err := r.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	rawPoints := make([]rawPoint, 0, filter.Limit)
	for rows.Next() {
		var point rawPoint
		if err := rows.Scan(
			&point.accountID,
			&point.totalAsset,
			&point.availableFund,
			&point.updatedAt,
			&point.initialCapital,
		); err != nil {
			return nil, err
		}
		rawPoints = append(rawPoints, point)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	reverseRawPoints(rawPoints)
	rawPoints = sampleRawPoints(rawPoints, filter.SampleMinutes)

	points := make([]model.NetValuePoint, 0, len(rawPoints))
	runningMax := 0.0
	for _, point := range rawPoints {
		unit := 0.0
		if point.initialCapital > 0 {
			unit = point.totalAsset / point.initialCapital
		}
		if unit > runningMax {
			runningMax = unit
		}
		drawdown := 0.0
		if runningMax > 0 {
			drawdown = unit/runningMax - 1
		}
		points = append(points, model.NetValuePoint{
			CreatedAt:       point.updatedAt.Format("2006-01-02 15:04:05"),
			AccountID:       point.accountID,
			TotalAsset:      point.totalAsset,
			AvailableFund:   point.availableFund,
			UnitNetWorth:    unit,
			CurrentDrawdown: drawdown,
		})
	}
	return points, nil
}

func reverseRawPoints(points []rawPoint) {
	for left, right := 0, len(points)-1; left < right; left, right = left+1, right-1 {
		points[left], points[right] = points[right], points[left]
	}
}

func sampleRawPoints(points []rawPoint, sampleMinutes int) []rawPoint {
	if sampleMinutes <= 0 || len(points) <= 1 {
		return points
	}
	sampled := make([]rawPoint, 0, len(points))
	bucketSeconds := int64(sampleMinutes * 60)
	var current rawPoint
	var currentBucket int64
	hasCurrent := false
	for _, point := range points {
		bucket := point.updatedAt.Unix() / bucketSeconds
		if !hasCurrent {
			current = point
			currentBucket = bucket
			hasCurrent = true
			continue
		}
		if bucket == currentBucket {
			current = point
			continue
		}
		sampled = append(sampled, current)
		current = point
		currentBucket = bucket
	}
	if hasCurrent {
		sampled = append(sampled, current)
	}
	return sampled
}

type accountScanner interface {
	Scan(dest ...interface{}) error
}

func scanAccountWithAsset(scanner accountScanner) (model.Account, error) {
	var account model.Account
	var parentID, ownerID sql.NullInt64
	var totalAsset, availableFund sql.NullFloat64
	var assetUpdatedAt sql.NullTime
	var arbitraryFlag bool
	var hasAPIKey, hasAPISecret bool
	if err := scanner.Scan(
		&account.ID,
		&account.Name,
		&account.AccountType,
		&account.AccountAddress,
		&account.InitialCapital,
		&parentID,
		&arbitraryFlag,
		&ownerID,
		&account.Status,
		&account.CreatedAt,
		&account.UpdatedAt,
		&hasAPIKey,
		&hasAPISecret,
		&totalAsset,
		&availableFund,
		&assetUpdatedAt,
	); err != nil {
		return model.Account{}, err
	}
	account.ArbitraryFlag = arbitraryFlag
	account.HasAPIKey = hasAPIKey
	account.HasAPISecret = hasAPISecret
	if parentID.Valid {
		account.ParentID = &parentID.Int64
	}
	if ownerID.Valid {
		account.OwnerID = &ownerID.Int64
	}
	if totalAsset.Valid {
		v := totalAsset.Float64
		account.TotalAsset = &v
	}
	if availableFund.Valid {
		v := availableFund.Float64
		account.AvailableFund = &v
	}
	if assetUpdatedAt.Valid {
		t := assetUpdatedAt.Time
		account.AssetUpdatedAt = &t
	}
	account.CheckCode = account.AccountAddress
	account.Platform = platformForAccountType(account.AccountType)
	account.AccountName = account.Name
	return account, nil
}

func scanAccountWithAssetAndCredentials(scanner accountScanner) (model.Account, error) {
	var account model.Account
	var parentID, ownerID sql.NullInt64
	var totalAsset, availableFund sql.NullFloat64
	var assetUpdatedAt sql.NullTime
	var arbitraryFlag bool
	var hasAPIKey, hasAPISecret bool
	var apiKeyEncrypted, apiSecretEncrypted sql.NullString
	if err := scanner.Scan(
		&account.ID,
		&account.Name,
		&account.AccountType,
		&account.AccountAddress,
		&account.InitialCapital,
		&parentID,
		&arbitraryFlag,
		&ownerID,
		&account.Status,
		&account.CreatedAt,
		&account.UpdatedAt,
		&hasAPIKey,
		&hasAPISecret,
		&apiKeyEncrypted,
		&apiSecretEncrypted,
		&totalAsset,
		&availableFund,
		&assetUpdatedAt,
	); err != nil {
		return model.Account{}, err
	}
	account.ArbitraryFlag = arbitraryFlag
	account.HasAPIKey = hasAPIKey
	account.HasAPISecret = hasAPISecret
	if apiKeyEncrypted.Valid {
		account.APIKeyEncrypted = apiKeyEncrypted.String
	}
	if apiSecretEncrypted.Valid {
		account.APISecretEncrypted = apiSecretEncrypted.String
	}
	if parentID.Valid {
		account.ParentID = &parentID.Int64
	}
	if ownerID.Valid {
		account.OwnerID = &ownerID.Int64
	}
	if totalAsset.Valid {
		v := totalAsset.Float64
		account.TotalAsset = &v
	}
	if availableFund.Valid {
		v := availableFund.Float64
		account.AvailableFund = &v
	}
	if assetUpdatedAt.Valid {
		t := assetUpdatedAt.Time
		account.AssetUpdatedAt = &t
	}
	account.CheckCode = account.AccountAddress
	account.Platform = platformForAccountType(account.AccountType)
	account.AccountName = account.Name
	return account, nil
}

func normalizePlatform(platform string) string {
	switch strings.ToLower(strings.TrimSpace(platform)) {
	case "", "crypto", "bybit":
		return "bybit"
	case "mt5":
		return "mt5_exam"
	case "futures", "shfe":
		return "puridia"
	default:
		return platform
	}
}

func platformForAccountType(accountType string) string {
	switch strings.ToLower(accountType) {
	case "bybit":
		return "crypto"
	case "mt5_exam":
		return "MT5"
	default:
		return accountType
	}
}

func nullableJSON(raw []byte) interface{} {
	if len(raw) == 0 {
		return nil
	}
	return string(raw)
}

func nullableString(value string) interface{} {
	value = strings.TrimSpace(value)
	if value == "" {
		return nil
	}
	return value
}
