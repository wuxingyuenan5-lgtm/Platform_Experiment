package handler

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"time"

	"data-service/internal/model"
	"data-service/internal/service"
)

type Handler struct {
	svc *service.DataService
}

func New(svc *service.DataService) *Handler {
	return &Handler{svc: svc}
}

func (h *Handler) Register(mux *http.ServeMux) {
	mux.HandleFunc("/health", h.health)
	mux.HandleFunc("/api/v1/accounts", h.accounts)
	mux.HandleFunc("/api/v1/accounts/", h.accountByID)
	mux.HandleFunc("/api/v1/data/sync", h.sync)
	mux.HandleFunc("/api/v1/data/total", h.total)
	mux.HandleFunc("/api/v1/data/net-value", h.netValue)

	mux.HandleFunc("/product/navplatformNetValueList", h.frontendNetValue)
	mux.HandleFunc("/product/nav/list", h.frontendNetValue)
	mux.HandleFunc("/product/nav/productRatio", h.frontendProductRatio)
	mux.HandleFunc("/exchange/", h.exchange)
}

func (h *Handler) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":           "ok",
		"service":          "data-service",
		"update_frequency": "5m",
	})
}

func (h *Handler) accounts(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		accounts, err := h.svc.ListAccounts(r.Context())
		if err != nil {
			writeError(w, http.StatusInternalServerError, err)
			return
		}
		writeEnvelope(w, accounts)
	case http.MethodPost:
		if !h.requireRole(w, r, "employee", "admin") {
			return
		}
		var account model.Account
		if err := json.NewDecoder(r.Body).Decode(&account); err != nil {
			writeError(w, http.StatusBadRequest, err)
			return
		}
		created, err := h.svc.CreateAccount(r.Context(), &account)
		if err != nil {
			writeError(w, http.StatusBadRequest, err)
			return
		}
		writeEnvelope(w, created)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (h *Handler) accountByID(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodDelete {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	idRaw := strings.TrimPrefix(r.URL.Path, "/api/v1/accounts/")
	id, err := strconv.ParseInt(strings.Trim(idRaw, "/"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	if r.Method == http.MethodDelete {
		if !h.requireRole(w, r, "admin") {
			return
		}
		if err := h.svc.DeleteAccount(r.Context(), id); err != nil {
			writeError(w, http.StatusBadRequest, err)
			return
		}
		writeEnvelope(w, map[string]string{"status": "deleted"})
		return
	}
	account, err := h.svc.GetAccount(r.Context(), id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if account == nil {
		writeErrorMessage(w, http.StatusNotFound, "account not found")
		return
	}
	writeEnvelope(w, account)
}

func (h *Handler) sync(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if !h.requireRole(w, r, "employee", "admin") {
		return
	}
	result, err := h.svc.SyncAccounts(r.Context())
	if err != nil {
		writeError(w, http.StatusBadGateway, err)
		return
	}
	writeEnvelope(w, result)
}

func (h *Handler) total(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	total, err := h.svc.Total(r.Context())
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	writeEnvelope(w, total)
}

func (h *Handler) netValue(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	points, err := h.svc.NetValueHistory(r.Context(), historyFilterFromRequest(r))
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	writeEnvelope(w, points)
}

func (h *Handler) frontendNetValue(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	points, err := h.svc.NetValueHistory(r.Context(), historyFilterFromRequest(r))
	if err != nil {
		writeFrontendError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeFrontend(w, points)
}

func (h *Handler) frontendProductRatio(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	accounts, err := h.svc.ListAccounts(r.Context())
	if err != nil {
		writeFrontendError(w, http.StatusInternalServerError, err.Error())
		return
	}
	total := 0.0
	for _, account := range accounts {
		if account.TotalAsset != nil {
			total += *account.TotalAsset
		}
	}
	data := make([]map[string]interface{}, 0, len(accounts))
	for _, account := range accounts {
		value := 0.0
		if account.TotalAsset != nil {
			value = *account.TotalAsset
		}
		percent := 0.0
		if total > 0 {
			percent = value / total
		}
		data = append(data, map[string]interface{}{
			"name":     account.Name,
			"value":    value,
			"valueUSD": value,
			"percent":  percent,
		})
	}
	writeFrontend(w, data)
}

func (h *Handler) exchange(w http.ResponseWriter, r *http.Request) {
	writeFrontend(w, map[string]interface{}{
		"rate":       1,
		"symbol":     "USD",
		"updated_at": time.Now().Format("2006-01-02 15:04:05"),
	})
}

func historyFilterFromRequest(r *http.Request) model.HistoryFilter {
	q := r.URL.Query()
	accountID, _ := strconv.ParseInt(q.Get("account_id"), 10, 64)
	if accountID == 0 {
		accountID, _ = strconv.ParseInt(q.Get("accountId"), 10, 64)
	}
	limit, _ := strconv.Atoi(q.Get("limit"))
	sampleMinutes, _ := strconv.Atoi(q.Get("sample_minutes"))
	if sampleMinutes == 0 {
		sampleMinutes, _ = strconv.Atoi(q.Get("sampleMinutes"))
	}
	filter := model.HistoryFilter{
		AccountID:     accountID,
		CheckCode:     q.Get("checkCode"),
		Platform:      q.Get("platform"),
		Limit:         limit,
		SampleMinutes: sampleMinutes,
	}
	if from := parseTimeParam(q.Get("from")); from != nil {
		filter.From = from
	}
	if to := parseTimeParam(q.Get("to")); to != nil {
		filter.To = to
	}
	return filter
}

func parseTimeParam(raw string) *time.Time {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	layouts := []string{time.RFC3339, "2006-01-02 15:04:05", "2006-01-02"}
	for _, layout := range layouts {
		if t, err := time.ParseInLocation(layout, raw, time.Local); err == nil {
			return &t
		}
	}
	return nil
}

func writeEnvelope(w http.ResponseWriter, data interface{}) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"code":    0,
		"message": "ok",
		"result":  data,
		"retCode": 0,
		"retMsg":  "ok",
		"data":    data,
	})
}

func writeFrontend(w http.ResponseWriter, data interface{}) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"retCode": 0,
		"retMsg":  "ok",
		"data":    data,
		"code":    0,
		"result":  data,
		"message": "ok",
	})
}

func writeError(w http.ResponseWriter, status int, err error) {
	writeErrorMessage(w, status, err.Error())
}

func writeErrorMessage(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]interface{}{
		"code":    status,
		"message": message,
		"retCode": status,
		"retMsg":  message,
	})
}

func writeFrontendError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]interface{}{
		"retCode": status,
		"retMsg":  message,
		"data":    []interface{}{},
		"code":    status,
		"message": message,
	})
}

func writeJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func (h *Handler) requireRole(w http.ResponseWriter, r *http.Request, allowed ...string) bool {
	secret := strings.TrimSpace(h.svc.JWTSecret())
	if secret == "" {
		writeErrorMessage(w, http.StatusForbidden, "JWT_SECRET is required")
		return false
	}
	claims, ok := parseBearerClaims(r.Header.Get("Authorization"), secret)
	if !ok {
		writeErrorMessage(w, http.StatusUnauthorized, "unauthorized")
		return false
	}
	role := strings.ToLower(strings.TrimSpace(stringClaim(claims, "role")))
	for _, item := range allowed {
		if role == item {
			return true
		}
	}
	writeErrorMessage(w, http.StatusForbidden, "permission denied")
	return false
}

func parseBearerClaims(auth, secret string) (map[string]interface{}, bool) {
	auth = strings.TrimSpace(auth)
	if strings.HasPrefix(auth, "Bearer ") {
		auth = strings.TrimSpace(strings.TrimPrefix(auth, "Bearer "))
	}
	parts := strings.Split(auth, ".")
	if len(parts) != 3 {
		return nil, false
	}
	signingInput := parts[0] + "." + parts[1]
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(signingInput))
	expected := mac.Sum(nil)
	actual, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil || !hmac.Equal(actual, expected) {
		return nil, false
	}
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, false
	}
	var claims map[string]interface{}
	if err := json.Unmarshal(payload, &claims); err != nil {
		return nil, false
	}
	if exp, ok := claims["exp"].(float64); ok && int64(exp) < time.Now().Unix() {
		return nil, false
	}
	return claims, true
}

func stringClaim(claims map[string]interface{}, key string) string {
	value, ok := claims[key]
	if !ok || value == nil {
		return ""
	}
	if text, ok := value.(string); ok {
		return text
	}
	return ""
}
