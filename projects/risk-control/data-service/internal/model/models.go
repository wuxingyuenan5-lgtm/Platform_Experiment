package model

import (
	"encoding/json"
	"time"
)

type Account struct {
	ID                 int64      `json:"id"`
	Name               string     `json:"name"`
	AccountType        string     `json:"account_type"`
	AccountAddress     string     `json:"account_address"`
	InitialCapital     float64    `json:"initial_capital"`
	ParentID           *int64     `json:"parent_id,omitempty"`
	ArbitraryFlag      bool       `json:"arbitrary_flag"`
	OwnerID            *int64     `json:"owner_id,omitempty"`
	Status             string     `json:"status"`
	CreatedAt          time.Time  `json:"created_at"`
	UpdatedAt          time.Time  `json:"updated_at"`
	TotalAsset         *float64   `json:"total_asset,omitempty"`
	AvailableFund      *float64   `json:"available_fund,omitempty"`
	AssetUpdatedAt     *time.Time `json:"asset_updated_at,omitempty"`
	APIKey             string     `json:"api_key,omitempty"`
	APISecret          string     `json:"api_secret,omitempty"`
	APIKeyEncrypted    string     `json:"-"`
	APISecretEncrypted string     `json:"-"`
	HasAPIKey          bool       `json:"has_api_key"`
	HasAPISecret       bool       `json:"has_api_secret"`

	CheckCode   string `json:"checkCode"`
	Platform    string `json:"platform"`
	AccountName string `json:"accountName"`
}

type AssetSnapshot struct {
	ID              int64           `json:"id"`
	AccountID       int64           `json:"account_id"`
	TotalAsset      float64         `json:"total_asset"`
	AvailableFund   float64         `json:"available_fund"`
	BybitPositions  json.RawMessage `json:"bybit_positions,omitempty"`
	UpdateFrequency string          `json:"update_frequency"`
	DataSource      string          `json:"data_source"`
	UpdatedAt       time.Time       `json:"updated_at"`
}

type WalletBalance struct {
	AccountType      string          `json:"account_type"`
	TotalEquity      float64         `json:"total_equity"`
	AvailableBalance float64         `json:"available_balance"`
	WalletBalance    float64         `json:"wallet_balance"`
	Raw              json.RawMessage `json:"raw"`
}

type NetValuePoint struct {
	CreatedAt       string  `json:"created_at"`
	AccountID       int64   `json:"account_id,omitempty"`
	TotalAsset      float64 `json:"total_asset"`
	AvailableFund   float64 `json:"available_fund"`
	UnitNetWorth    float64 `json:"unit_net_worth"`
	CurrentDrawdown float64 `json:"current_drawdown"`
}

type SyncResult struct {
	AccountID       int64     `json:"account_id"`
	AccountName     string    `json:"account_name"`
	AccountType     string    `json:"account_type,omitempty"`
	TotalAsset      float64   `json:"total_asset"`
	AvailableFund   float64   `json:"available_fund"`
	SyncedAt        time.Time `json:"synced_at"`
	UpdateFrequency string    `json:"update_frequency"`
	DataSource      string    `json:"data_source"`
	Status          string    `json:"status,omitempty"`
	Message         string    `json:"message,omitempty"`
}

type SyncAccountsResult struct {
	Synced          int          `json:"synced"`
	Failed          int          `json:"failed"`
	Skipped         int          `json:"skipped"`
	TotalAsset      float64      `json:"total_asset"`
	AvailableFund   float64      `json:"available_fund"`
	SyncedAt        time.Time    `json:"synced_at"`
	UpdateFrequency string       `json:"update_frequency"`
	Results         []SyncResult `json:"results"`
}

type HistoryFilter struct {
	AccountID     int64
	CheckCode     string
	Platform      string
	From          *time.Time
	To            *time.Time
	Limit         int
	SampleMinutes int
}
