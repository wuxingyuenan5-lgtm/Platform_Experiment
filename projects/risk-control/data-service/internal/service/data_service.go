package service

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"io"
	"strings"
	"sync"
	"time"

	"data-service/internal/config"
	"data-service/internal/model"
	apiadapter "data-service/internal/repository/api"
	mysqlrepo "data-service/internal/repository/mysql"
)

type DataService struct {
	cfg    config.Config
	repo   *mysqlrepo.Repository
	bybit  *apiadapter.BybitClient
	syncMu sync.Mutex
}

const (
	snapshotKindCurrent   = "current"
	snapshotKindValuation = "valuation"
)

func NewDataService(cfg config.Config, repo *mysqlrepo.Repository, bybit *apiadapter.BybitClient) *DataService {
	return &DataService{cfg: cfg, repo: repo, bybit: bybit}
}

func (s *DataService) JWTSecret() string {
	return s.cfg.JWTSecret
}

func (s *DataService) SyncAccounts(ctx context.Context) (*model.SyncAccountsResult, error) {
	return s.syncAccounts(ctx, snapshotKindCurrent, time.Now())
}

func (s *DataService) RecordAccountNetValues(ctx context.Context) (*model.SyncAccountsResult, error) {
	return s.syncAccounts(ctx, snapshotKindValuation, s.alignedSnapshotTime(time.Now()))
}

func (s *DataService) syncAccounts(ctx context.Context, snapshotKind string, snapshotTime time.Time) (*model.SyncAccountsResult, error) {
	s.syncMu.Lock()
	defer s.syncMu.Unlock()

	accounts, err := s.repo.ListAccountsForSync(ctx)
	if err != nil {
		return nil, err
	}
	result := &model.SyncAccountsResult{
		SyncedAt:        snapshotTime,
		UpdateFrequency: "5m",
		Results:         make([]model.SyncResult, 0, len(accounts)),
	}
	for _, account := range accounts {
		item := model.SyncResult{
			AccountID:       account.ID,
			AccountName:     account.Name,
			AccountType:     account.AccountType,
			SyncedAt:        result.SyncedAt,
			UpdateFrequency: "5m",
			DataSource:      account.AccountType,
		}
		switch account.AccountType {
		case "bybit":
			if account.APIKeyEncrypted == "" || account.APISecretEncrypted == "" {
				item.Status = "skipped"
				item.Message = "api credentials are missing"
				result.Skipped++
				result.Results = append(result.Results, item)
				continue
			}
			apiKey, err := s.decryptSecret(account.APIKeyEncrypted)
			if err != nil {
				item.Status = "failed"
				item.Message = err.Error()
				result.Failed++
				result.Results = append(result.Results, item)
				continue
			}
			apiSecret, err := s.decryptSecret(account.APISecretEncrypted)
			if err != nil {
				item.Status = "failed"
				item.Message = err.Error()
				result.Failed++
				result.Results = append(result.Results, item)
				continue
			}
			balance, err := s.fetchBybitAccountBalance(ctx, &account, apiKey, apiSecret)
			if err != nil {
				item.Status = "failed"
				item.Message = err.Error()
				result.Failed++
				result.Results = append(result.Results, item)
				continue
			}
			if err := s.repo.InsertAssetSnapshot(ctx, account.ID, balance, snapshotKind, snapshotTime); err != nil {
				item.Status = "failed"
				item.Message = err.Error()
				result.Failed++
				result.Results = append(result.Results, item)
				continue
			}
			item.Status = "synced"
			item.TotalAsset = balance.TotalEquity
			item.AvailableFund = balance.AvailableBalance
			result.Synced++
			result.TotalAsset += balance.TotalEquity
			result.AvailableFund += balance.AvailableBalance
			result.Results = append(result.Results, item)
		default:
			item.Status = "skipped"
			item.Message = "sync adapter is not implemented"
			result.Skipped++
			result.Results = append(result.Results, item)
		}
	}
	return result, nil
}

func (s *DataService) alignedSnapshotTime(now time.Time) time.Time {
	interval := s.cfg.SyncInterval
	if interval <= 0 {
		interval = 5 * time.Minute
	}
	return now.Truncate(interval)
}

func (s *DataService) ListAccounts(ctx context.Context) ([]model.Account, error) {
	return s.repo.ListAccounts(ctx)
}

func (s *DataService) CreateAccount(ctx context.Context, account *model.Account) (*model.Account, error) {
	account.Name = strings.TrimSpace(account.Name)
	account.AccountType = strings.ToLower(strings.TrimSpace(account.AccountType))
	account.AccountAddress = strings.TrimSpace(account.AccountAddress)
	account.APIKey = strings.TrimSpace(account.APIKey)
	account.APISecret = strings.TrimSpace(account.APISecret)
	rawAPIKey := account.APIKey
	rawAPISecret := account.APISecret
	if account.Name == "" {
		return nil, errors.New("name is required")
	}
	if account.AccountType == "" {
		account.AccountType = "bybit"
	}
	if account.AccountAddress == "" {
		return nil, errors.New("account_address is required")
	}
	var initialBalance *model.WalletBalance
	if account.AccountType == "bybit" {
		if rawAPIKey == "" || rawAPISecret == "" {
			return nil, errors.New("api_key and api_secret are required for bybit accounts")
		}
		balance, err := s.fetchBybitAccountBalance(ctx, account, rawAPIKey, rawAPISecret)
		if err != nil {
			return nil, err
		}
		initialBalance = balance
	}
	if account.APIKey != "" {
		encrypted, err := s.encryptSecret(account.APIKey)
		if err != nil {
			return nil, err
		}
		account.APIKeyEncrypted = encrypted
	}
	if account.APISecret != "" {
		encrypted, err := s.encryptSecret(account.APISecret)
		if err != nil {
			return nil, err
		}
		account.APISecretEncrypted = encrypted
	}
	account.APIKey = ""
	account.APISecret = ""
	created, err := s.repo.CreateAccount(ctx, account)
	if err != nil {
		return nil, err
	}
	if initialBalance != nil {
		if err := s.repo.InsertAssetSnapshot(ctx, created.ID, initialBalance, snapshotKindCurrent, time.Now()); err != nil {
			return nil, err
		}
		refreshed, err := s.repo.GetAccountByID(ctx, created.ID)
		if err == nil && refreshed != nil {
			return refreshed, nil
		}
	}
	return created, nil
}

func (s *DataService) GetAccount(ctx context.Context, id int64) (*model.Account, error) {
	return s.repo.GetAccountByID(ctx, id)
}

func (s *DataService) DeleteAccount(ctx context.Context, id int64) error {
	if id <= 0 {
		return errors.New("invalid account id")
	}
	return s.repo.DeleteAccount(ctx, id)
}

func (s *DataService) NetValueHistory(ctx context.Context, filter model.HistoryFilter) ([]model.NetValuePoint, error) {
	return s.repo.NetValueHistory(ctx, filter)
}

func (s *DataService) Total(ctx context.Context) (map[string]interface{}, error) {
	total, updatedAt, err := s.repo.TotalAssets(ctx)
	if err != nil {
		return nil, err
	}
	return map[string]interface{}{
		"total_asset":      total,
		"asset_updated_at": updatedAt.Format("2006-01-02 15:04:05"),
		"update_frequency": "5m",
		"data_source":      "bybit",
	}, nil
}

func (s *DataService) encryptSecret(raw string) (string, error) {
	if strings.TrimSpace(raw) == "" {
		return "", nil
	}
	keyText := strings.TrimSpace(s.cfg.AccountSecretKey)
	if keyText == "" {
		return "", errors.New("ACCOUNT_ENCRYPTION_KEY is required to save API credentials")
	}
	key := sha256.Sum256([]byte(keyText))
	block, err := aes.NewCipher(key[:])
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}
	payload := append(nonce, gcm.Seal(nil, nonce, []byte(raw), nil)...)
	return base64.StdEncoding.EncodeToString(payload), nil
}

func (s *DataService) decryptSecret(encrypted string) (string, error) {
	encrypted = strings.TrimSpace(encrypted)
	if encrypted == "" {
		return "", nil
	}
	keyText := strings.TrimSpace(s.cfg.AccountSecretKey)
	if keyText == "" {
		return "", errors.New("ACCOUNT_ENCRYPTION_KEY is required to read API credentials")
	}
	payload, err := base64.StdEncoding.DecodeString(encrypted)
	if err != nil {
		return "", err
	}
	key := sha256.Sum256([]byte(keyText))
	block, err := aes.NewCipher(key[:])
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonceSize := gcm.NonceSize()
	if len(payload) < nonceSize {
		return "", errors.New("encrypted credential is invalid")
	}
	raw, err := gcm.Open(nil, payload[:nonceSize], payload[nonceSize:], nil)
	if err != nil {
		return "", err
	}
	return string(raw), nil
}

func (s *DataService) fetchBybitAccountBalance(ctx context.Context, account *model.Account, apiKey, apiSecret string) (*model.WalletBalance, error) {
	cfg := s.cfg.Bybit
	cfg.APIKey = apiKey
	cfg.APISecret = apiSecret
	cfg.AccountName = account.Name
	cfg.AccountAddress = account.AccountAddress
	client := apiadapter.NewBybitClient(cfg, nil)
	return client.WalletBalance(ctx)
}
