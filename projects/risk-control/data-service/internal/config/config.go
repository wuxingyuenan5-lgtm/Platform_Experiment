package config

import (
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/go-sql-driver/mysql"
)

type Config struct {
	DBDSN            string
	Host             string
	Port             string
	JWTSecret        string
	AccountSecretKey string
	AutoMigrate      bool
	SchedulerEnabled bool
	SyncOnStart      bool
	SyncInterval     time.Duration
	Bybit            BybitConfig
}

type BybitConfig struct {
	APIKey          string
	APISecret       string
	BaseURL         string
	AccountType     string
	Coin            string
	RecvWindow      string
	TimestampOffset time.Duration
	CredentialFile  string
	AccountName     string
	AccountAddress  string
	InitialCapital  float64
}

func Load() (Config, error) {
	appLocation := beijingLocation()
	time.Local = appLocation

	cfg := Config{
		DBDSN:            strings.TrimSpace(os.Getenv("DB_DSN")),
		Host:             getenv("HOST", "127.0.0.1"),
		Port:             getenv("PORT", "8082"),
		JWTSecret:        strings.TrimSpace(os.Getenv("JWT_SECRET")),
		AccountSecretKey: strings.TrimSpace(os.Getenv("ACCOUNT_ENCRYPTION_KEY")),
		AutoMigrate:      getenvBool("AUTO_MIGRATE", true),
		SchedulerEnabled: getenvBool("SCHEDULER_ENABLED", true),
		SyncOnStart:      getenvBool("SYNC_ON_START", true),
		SyncInterval:     5 * time.Minute,
		Bybit: BybitConfig{
			APIKey:          strings.TrimSpace(os.Getenv("BYBIT_API_KEY")),
			APISecret:       strings.TrimSpace(os.Getenv("BYBIT_API_SECRET")),
			BaseURL:         strings.TrimRight(getenv("BYBIT_BASE_URL", "https://api.bybit.com"), "/"),
			AccountType:     getenv("BYBIT_ACCOUNT_TYPE", "UNIFIED"),
			Coin:            strings.TrimSpace(os.Getenv("BYBIT_COIN")),
			RecvWindow:      getenv("BYBIT_RECV_WINDOW", "10000"),
			TimestampOffset: 0,
			CredentialFile:  getenv("BYBIT_CREDENTIAL_FILE", "bitget-data-service/bybitapi.txt"),
			AccountName:     getenv("BYBIT_ACCOUNT_NAME", "Bybit Unified Account"),
			AccountAddress:  getenv("BYBIT_ACCOUNT_ADDRESS", "bybit-unified"),
		},
	}

	if raw := strings.TrimSpace(os.Getenv("SYNC_INTERVAL")); raw != "" {
		d, err := time.ParseDuration(raw)
		if err != nil {
			return Config{}, err
		}
		cfg.SyncInterval = d
	}
	if raw := strings.TrimSpace(os.Getenv("BYBIT_INITIAL_CAPITAL")); raw != "" {
		v, err := strconv.ParseFloat(raw, 64)
		if err != nil {
			return Config{}, err
		}
		cfg.Bybit.InitialCapital = v
	}
	if raw := strings.TrimSpace(os.Getenv("BYBIT_TIMESTAMP_OFFSET_MS")); raw != "" {
		v, err := strconv.ParseInt(raw, 10, 64)
		if err != nil {
			return Config{}, err
		}
		cfg.Bybit.TimestampOffset = time.Duration(v) * time.Millisecond
	}
	if cfg.DBDSN == "" {
		return Config{}, errors.New("DB_DSN environment variable is required")
	}
	cfg.DBDSN = normalizeMySQLDSN(cfg.DBDSN, appLocation)
	if cfg.AccountSecretKey == "" {
		cfg.AccountSecretKey = cfg.JWTSecret
	}

	if cfg.Bybit.APIKey == "" || cfg.Bybit.APISecret == "" {
		key, secret := readBybitCredentials(cfg.Bybit.CredentialFile)
		if cfg.Bybit.APIKey == "" {
			cfg.Bybit.APIKey = key
		}
		if cfg.Bybit.APISecret == "" {
			cfg.Bybit.APISecret = secret
		}
	}

	return cfg, nil
}

func beijingLocation() *time.Location {
	loc, err := time.LoadLocation("Asia/Shanghai")
	if err != nil {
		return time.FixedZone("CST", 8*60*60)
	}
	return loc
}

func normalizeMySQLDSN(raw string, loc *time.Location) string {
	cfg, err := mysql.ParseDSN(raw)
	if err != nil {
		return raw
	}
	cfg.ParseTime = true
	cfg.Loc = loc
	if cfg.Params == nil {
		cfg.Params = map[string]string{}
	}
	if _, ok := cfg.Params["time_zone"]; !ok {
		cfg.Params["time_zone"] = "'+08:00'"
	}
	return cfg.FormatDSN()
}

func getenv(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func getenvBool(key string, fallback bool) bool {
	raw := strings.TrimSpace(os.Getenv(key))
	if raw == "" {
		return fallback
	}
	v, err := strconv.ParseBool(raw)
	if err != nil {
		return fallback
	}
	return v
}

func readBybitCredentials(path string) (string, string) {
	candidates := []string{path}
	if !filepath.IsAbs(path) {
		candidates = append(candidates,
			filepath.Join(".", path),
			filepath.Join("..", path),
		)
	}

	for _, candidate := range candidates {
		body, err := os.ReadFile(candidate)
		if err != nil {
			continue
		}
		return parseCredentialText(string(body))
	}
	return "", ""
}

func parseCredentialText(raw string) (string, string) {
	lines := strings.Split(raw, "\n")
	var key, secret string
	for i := 0; i < len(lines); i++ {
		line := strings.TrimSpace(lines[i])
		lower := strings.ToLower(line)
		switch {
		case lower == "key:" || lower == "api_key:" || lower == "apikey:":
			if i+1 < len(lines) {
				key = strings.TrimSpace(lines[i+1])
			}
		case strings.HasPrefix(lower, "key:"):
			key = strings.TrimSpace(line[strings.Index(line, ":")+1:])
		case lower == "secret:" || lower == "api_secret:" || lower == "apisecret:":
			if i+1 < len(lines) {
				secret = strings.TrimSpace(lines[i+1])
			}
		case strings.HasPrefix(lower, "secret:"):
			secret = strings.TrimSpace(line[strings.Index(line, ":")+1:])
		}
	}
	return key, secret
}
