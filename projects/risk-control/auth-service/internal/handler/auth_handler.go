package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"auth-service/internal/service"
)

type AuthHandler struct {
	svc *service.AuthService
}

func NewAuthHandler(s *service.AuthService) *AuthHandler { return &AuthHandler{svc: s} }

func (h *AuthHandler) HandleRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/health", h.Health)
	mux.HandleFunc("/register", h.Register)
	mux.HandleFunc("/login", h.Login)
	mux.HandleFunc("/refresh", h.Refresh)
	mux.HandleFunc("/me", h.Me)
	// provide menus for frontend permission / sidebar during dev
	mux.HandleFunc("/menus", h.Menus)
	mux.HandleFunc("/api/v1/users/registrations", h.RegistrationRequests)
	mux.HandleFunc("/api/v1/users/registrations/", h.RegistrationRequestByID)

	// Local dev stubs for frontend features
	mux.HandleFunc("/notifications/api/v1/messages/", h.Notifications)
	mux.HandleFunc("/risk/api/v1/risk-records/", h.RiskRecords)
}

func (h *AuthHandler) Health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok", "service": "auth-service"})
}

// Notifications returns a simple paged messages response compatible with frontend format
func (h *AuthHandler) Notifications(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	resp := map[string]interface{}{
		"code": 0,
		"result": map[string]interface{}{
			"items": []map[string]interface{}{{"id": 1, "title": "Welcome", "content": "Welcome to the system", "isRead": false}},
			"total": 1,
		},
		"message": "ok",
		"retCode": 0,
		"data":    map[string]interface{}{"items": []map[string]interface{}{{"id": 1, "title": "Welcome", "content": "Welcome to the system", "isRead": false}}, "total": 1},
		"retMsg":  "ok",
	}
	json.NewEncoder(w).Encode(resp)
}

// RiskRecords returns a simple list of risk records
func (h *AuthHandler) RiskRecords(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	resp := map[string]interface{}{
		"code": 0,
		"result": map[string]interface{}{
			"items": []map[string]interface{}{},
			"total": 0,
		},
		"message": "ok",
		"retCode": 0,
		"data":    map[string]interface{}{"items": []map[string]interface{}{}, "total": 0},
		"retMsg":  "ok",
	}
	json.NewEncoder(w).Encode(resp)
}

// Menus returns a simple menu tree used by frontend to populate sidebar during dev
func (h *AuthHandler) Menus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	menus := []map[string]interface{}{
		map[string]interface{}{"path": "/dashboard", "name": "Dashboard", "meta": map[string]interface{}{"title": "仪表盘", "icon": "ant-design:dashboard-outlined"}},
		map[string]interface{}{"path": "/risk", "name": "Risk", "meta": map[string]interface{}{"title": "风险", "icon": "ant-design:warning-outlined"}},
		map[string]interface{}{"path": "/users", "name": "Users", "meta": map[string]interface{}{"title": "用户", "icon": "ant-design:user-outlined"}},
		map[string]interface{}{"path": "/reports", "name": "Reports", "meta": map[string]interface{}{"title": "报表", "icon": "ant-design:bar-chart-outlined"}},
		map[string]interface{}{"path": "/finance", "name": "Finance", "meta": map[string]interface{}{"title": "财务", "icon": "ant-design:wallet-outlined"}},
		map[string]interface{}{"path": "/strategy", "name": "Strategy", "meta": map[string]interface{}{"title": "策略", "icon": "ant-design:rocket-outlined"}},
		map[string]interface{}{"path": "/settings", "name": "Settings", "meta": map[string]interface{}{"title": "设置", "icon": "ant-design:setting-outlined"}},
	}
	resp := map[string]interface{}{"code": 0, "data": menus, "result": menus, "message": "ok", "retCode": 0}
	json.NewEncoder(w).Encode(resp)
}

func decode(r *http.Request, v interface{}) error { return json.NewDecoder(r.Body).Decode(v) }

func (h *AuthHandler) Register(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		Username      string `json:"username"`
		Name          string `json:"name"`
		Password      string `json:"password"`
		Email         string `json:"email"`
		Role          string `json:"role"`
		RequestedRole string `json:"requested_role"`
		Department    string `json:"department"`
	}
	if err := decode(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "bad request")
		return
	}
	username := strings.TrimSpace(req.Username)
	if username == "" {
		username = strings.TrimSpace(req.Name)
	}
	requestedRole := strings.TrimSpace(req.RequestedRole)
	if requestedRole == "" {
		requestedRole = strings.TrimSpace(req.Role)
	}
	var department *string
	if value := strings.TrimSpace(req.Department); value != "" {
		department = &value
	}
	u, err := h.svc.Register(username, req.Password, req.Email, requestedRole, department)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeEnvelope(w, map[string]interface{}{
		"user":    u,
		"message": "注册申请已提交，请等待管理员审核",
	})
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var req map[string]interface{}
	if err := decode(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "bad request")
		return
	}

	username := stringField(req, "username")
	if username == "" {
		username = stringField(req, "name")
	}
	if username == "" {
		writeError(w, http.StatusBadRequest, "username is required")
		return
	}

	password := stringField(req, "password")
	if password == "" {
		writeError(w, http.StatusBadRequest, "password is required")
		return
	}

	u, err := h.svc.Authenticate(username, password)
	if err != nil {
		writeError(w, http.StatusUnauthorized, err.Error())
		return
	}

	accessTTL := 15 * time.Minute
	access, err := h.svc.IssueAccessToken(u, accessTTL)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "token error")
		return
	}

	refreshTTL := 7 * 24 * time.Hour
	rid, err := h.svc.CreateRefreshSession(u.ID, time.Now().Add(refreshTTL))
	if err != nil {
		writeError(w, http.StatusInternalServerError, "session error")
		return
	}

	resp := map[string]interface{}{
		"access_token":  access,
		"expires_in":    int(accessTTL.Seconds()),
		"refresh_token": rid,
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func (h *AuthHandler) RegistrationRequests(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	if _, ok := h.requireAdmin(w, r); !ok {
		return
	}
	users, err := h.svc.ListRegistrationRequests(r.URL.Query().Get("status"))
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeEnvelope(w, users)
}

func (h *AuthHandler) RegistrationRequestByID(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	adminID, ok := h.requireAdmin(w, r)
	if !ok {
		return
	}
	rest := strings.TrimPrefix(r.URL.Path, "/api/v1/users/registrations/")
	parts := strings.Split(strings.Trim(rest, "/"), "/")
	if len(parts) != 2 {
		writeError(w, http.StatusNotFound, "not found")
		return
	}
	id, err := strconv.ParseInt(parts[0], 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid user id")
		return
	}
	switch parts[1] {
	case "approve":
		err = h.svc.ApproveRegistration(id, adminID)
	case "reject":
		var req struct {
			Reason string `json:"reason"`
		}
		_ = decode(r, &req)
		err = h.svc.RejectRegistration(id, adminID, req.Reason)
	default:
		writeError(w, http.StatusNotFound, "not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	writeEnvelope(w, map[string]string{"status": "ok"})
}

func (h *AuthHandler) Refresh(w http.ResponseWriter, r *http.Request) {
	var req struct{ RefreshToken string }
	if err := decode(r, &req); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	s, err := h.svc.ValidateRefresh(req.RefreshToken)
	if err != nil {
		http.Error(w, "invalid refresh", http.StatusUnauthorized)
		return
	}
	u, err := h.svc.GetUserByID(s.UserID)
	if err != nil || u == nil {
		http.Error(w, "user not found", http.StatusUnauthorized)
		return
	}
	access, err := h.svc.IssueAccessToken(u, 15*time.Minute)
	if err != nil {
		http.Error(w, "token error", http.StatusInternalServerError)
		return
	}
	json.NewEncoder(w).Encode(map[string]interface{}{"access_token": access, "expires_in": 900})
}

func (h *AuthHandler) Me(w http.ResponseWriter, r *http.Request) {
	// simple: read Authorization Bearer token
	auth := r.Header.Get("Authorization")
	if auth == "" {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}
	// decode manually via env JWT_SECRET
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		http.Error(w, "server misconfigured", http.StatusInternalServerError)
		return
	}
	// validate
	claims, ok := service.ParseToken(auth, []byte(secret))
	if !ok {
		http.Error(w, "invalid token", http.StatusUnauthorized)
		return
	}
	json.NewEncoder(w).Encode(claims)
}

func (h *AuthHandler) requireAdmin(w http.ResponseWriter, r *http.Request) (int64, bool) {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		writeError(w, http.StatusInternalServerError, "server misconfigured")
		return 0, false
	}
	claims, ok := service.ParseToken(r.Header.Get("Authorization"), []byte(secret))
	if !ok {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return 0, false
	}
	role := strings.ToLower(strings.TrimSpace(stringField(claims, "role")))
	if role != "admin" && role != "super" {
		writeError(w, http.StatusForbidden, "admin role is required")
		return 0, false
	}
	return int64Field(claims, "sub"), true
}

func stringField(data map[string]interface{}, key string) string {
	value, ok := data[key]
	if !ok || value == nil {
		return ""
	}
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	default:
		return strings.TrimSpace(fmt.Sprint(typed))
	}
}

func int64Field(data map[string]interface{}, key string) int64 {
	value, ok := data[key]
	if !ok || value == nil {
		return 0
	}
	switch typed := value.(type) {
	case int64:
		return typed
	case int:
		return int64(typed)
	case float64:
		return int64(typed)
	case string:
		v, _ := strconv.ParseInt(typed, 10, 64)
		return v
	default:
		return 0
	}
}

func writeEnvelope(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"code":    0,
		"message": "ok",
		"result":  data,
		"retCode": 0,
		"retMsg":  "ok",
		"data":    data,
	})
}

func writeError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"code":    status,
		"message": message,
		"retCode": status,
		"retMsg":  message,
	})
}
