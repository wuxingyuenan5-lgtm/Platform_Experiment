package api

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"data-service/internal/config"
	"data-service/internal/model"
)

var ErrMissingCredentials = errors.New("bybit credentials are missing")

type BybitClient struct {
	cfg        config.BybitConfig
	httpClient *http.Client
	now        func() time.Time
}

func NewBybitClient(cfg config.BybitConfig, httpClient *http.Client) *BybitClient {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 20 * time.Second}
	}
	return &BybitClient{
		cfg:        cfg,
		httpClient: httpClient,
		now:        time.Now,
	}
}

func (c *BybitClient) WalletBalance(ctx context.Context) (*model.WalletBalance, error) {
	if c.cfg.APIKey == "" || c.cfg.APISecret == "" {
		return nil, ErrMissingCredentials
	}
	query := url.Values{}
	query.Set("accountType", c.cfg.AccountType)
	if c.cfg.Coin != "" {
		query.Set("coin", c.cfg.Coin)
	}
	queryString := query.Encode()
	timestampMillis := c.now().Add(c.cfg.TimestampOffset).UnixMilli()
	if serverTime, err := c.serverTime(ctx); err == nil {
		timestampMillis = serverTime.Add(c.cfg.TimestampOffset).UnixMilli()
	}
	timestamp := strconv.FormatInt(timestampMillis, 10)
	sign := signBybitRequest(timestamp, c.cfg.APIKey, c.cfg.RecvWindow, queryString, c.cfg.APISecret)

	endpoint := c.cfg.BaseURL + "/v5/account/wallet-balance?" + queryString
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-BAPI-API-KEY", c.cfg.APIKey)
	req.Header.Set("X-BAPI-SIGN", sign)
	req.Header.Set("X-BAPI-TIMESTAMP", timestamp)
	req.Header.Set("X-BAPI-RECV-WINDOW", c.cfg.RecvWindow)
	req.Header.Set("X-BAPI-SIGN-TYPE", "2")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("bybit wallet balance http %d: %s", resp.StatusCode, string(body))
	}

	var payload walletBalanceResponse
	if err := json.Unmarshal(body, &payload); err != nil {
		return nil, err
	}
	if payload.RetCode != 0 {
		return nil, fmt.Errorf("bybit wallet balance retCode %d: %s", payload.RetCode, payload.RetMsg)
	}
	if len(payload.Result.List) == 0 {
		return nil, errors.New("bybit wallet balance returned an empty account list")
	}

	account := payload.Result.List[0]
	raw, err := json.Marshal(account)
	if err != nil {
		return nil, err
	}
	totalEquity := parseBybitDecimal(account.TotalEquity)
	walletBalance := parseBybitDecimal(account.TotalWalletBalance)
	available := parseBybitDecimal(account.TotalAvailableBalance)
	if totalEquity == 0 {
		for _, coin := range account.Coin {
			totalEquity += parseBybitDecimal(coin.USDValue)
		}
	}
	if available == 0 {
		available = parseBybitDecimal(account.TotalMarginBalance)
	}
	if available == 0 {
		available = walletBalance
	}

	return &model.WalletBalance{
		AccountType:      account.AccountType,
		TotalEquity:      totalEquity,
		AvailableBalance: available,
		WalletBalance:    walletBalance,
		Raw:              raw,
	}, nil
}

func (c *BybitClient) serverTime(ctx context.Context) (time.Time, error) {
	endpoint := c.cfg.BaseURL + "/v5/market/time"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return time.Time{}, err
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return time.Time{}, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return time.Time{}, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return time.Time{}, fmt.Errorf("bybit server time http %d: %s", resp.StatusCode, string(body))
	}

	var payload serverTimeResponse
	if err := json.Unmarshal(body, &payload); err != nil {
		return time.Time{}, err
	}
	if payload.RetCode != 0 {
		return time.Time{}, fmt.Errorf("bybit server time retCode %d: %s", payload.RetCode, payload.RetMsg)
	}
	if payload.Time > 0 {
		return time.UnixMilli(payload.Time), nil
	}
	if payload.Result.TimeSecond != "" {
		seconds, err := strconv.ParseInt(payload.Result.TimeSecond, 10, 64)
		if err == nil {
			return time.Unix(seconds, 0), nil
		}
	}
	if payload.Result.TimeNano != "" {
		nanos, err := strconv.ParseInt(strings.TrimSpace(payload.Result.TimeNano), 10, 64)
		if err == nil {
			return time.Unix(0, nanos), nil
		}
	}
	return time.Time{}, errors.New("bybit server time response did not include a usable timestamp")
}

func signBybitRequest(timestamp, apiKey, recvWindow, queryString, secret string) string {
	payload := timestamp + apiKey + recvWindow + queryString
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(payload))
	return hex.EncodeToString(mac.Sum(nil))
}

func parseBybitDecimal(raw string) float64 {
	if raw == "" {
		return 0
	}
	v, err := strconv.ParseFloat(raw, 64)
	if err != nil {
		return 0
	}
	return v
}

type walletBalanceResponse struct {
	RetCode int    `json:"retCode"`
	RetMsg  string `json:"retMsg"`
	Result  struct {
		List []walletBalanceAccount `json:"list"`
	} `json:"result"`
	Time int64 `json:"time"`
}

type serverTimeResponse struct {
	RetCode int    `json:"retCode"`
	RetMsg  string `json:"retMsg"`
	Result  struct {
		TimeSecond string `json:"timeSecond"`
		TimeNano   string `json:"timeNano"`
	} `json:"result"`
	Time int64 `json:"time"`
}

type walletBalanceAccount struct {
	AccountType           string              `json:"accountType"`
	TotalEquity           string              `json:"totalEquity"`
	TotalWalletBalance    string              `json:"totalWalletBalance"`
	TotalMarginBalance    string              `json:"totalMarginBalance"`
	TotalAvailableBalance string              `json:"totalAvailableBalance"`
	Coin                  []walletBalanceCoin `json:"coin"`
}

type walletBalanceCoin struct {
	Coin          string `json:"coin"`
	Equity        string `json:"equity"`
	USDValue      string `json:"usdValue"`
	WalletBalance string `json:"walletBalance"`
}
