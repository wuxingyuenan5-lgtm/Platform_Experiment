package api

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"data-service/internal/config"
)

func TestWalletBalanceSignsAndParsesResponse(t *testing.T) {
	apiKey := "test-key"
	secret := "test-secret"
	recvWindow := "5000"

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v5/market/time" {
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{
				"retCode": 0,
				"retMsg": "OK",
				"result": {
					"timeSecond": "1710000000",
					"timeNano": "1710000000000000000"
				},
				"time": 1710000000000
			}`))
			return
		}
		if r.URL.Path != "/v5/account/wallet-balance" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		query := r.URL.RawQuery
		timestamp := r.Header.Get("X-BAPI-TIMESTAMP")
		if timestamp != "1710000000000" {
			t.Fatalf("unexpected timestamp %s", timestamp)
		}
		expected := expectedSignature(timestamp+apiKey+recvWindow+query, secret)
		if got := r.Header.Get("X-BAPI-SIGN"); got != expected {
			t.Fatalf("signature mismatch: got %s want %s", got, expected)
		}
		if got := r.Header.Get("X-BAPI-API-KEY"); got != apiKey {
			t.Fatalf("api key header mismatch: %s", got)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"retCode": 0,
			"retMsg": "OK",
			"result": {
				"list": [{
					"accountType": "UNIFIED",
					"totalEquity": "123.45",
					"totalWalletBalance": "120.00",
					"totalAvailableBalance": "100.25",
					"coin": [{"coin": "USDT", "usdValue": "123.45"}]
				}]
			},
			"time": 1710000000000
		}`))
	}))
	defer server.Close()

	client := NewBybitClient(config.BybitConfig{
		APIKey:      apiKey,
		APISecret:   secret,
		BaseURL:     server.URL,
		AccountType: "UNIFIED",
		RecvWindow:  recvWindow,
	}, server.Client())
	client.now = func() time.Time { return time.UnixMilli(1710000000000) }

	balance, err := client.WalletBalance(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if balance.TotalEquity != 123.45 {
		t.Fatalf("unexpected total equity %v", balance.TotalEquity)
	}
	if balance.AvailableBalance != 100.25 {
		t.Fatalf("unexpected available balance %v", balance.AvailableBalance)
	}
}

func expectedSignature(payload, secret string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(payload))
	return hex.EncodeToString(mac.Sum(nil))
}
