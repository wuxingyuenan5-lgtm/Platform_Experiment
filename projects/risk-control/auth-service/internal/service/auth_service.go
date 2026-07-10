package service

import (
	"errors"
	"strings"
	"time"

	"auth-service/internal/model"
	"auth-service/internal/repository/mysql"
	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"
)

type AuthService struct {
	repo      *mysqlrepo.UserRepository
	jwtSecret []byte
}

func NewAuthService(r *mysqlrepo.UserRepository, secret []byte) *AuthService {
	return &AuthService{repo: r, jwtSecret: secret}
}

func (s *AuthService) Register(username, password, email, requestedRole string, department *string) (*model.User, error) {
	username = strings.TrimSpace(username)
	email = strings.TrimSpace(email)
	requestedRole = normalizeRole(requestedRole)
	if username == "" {
		return nil, errors.New("username is required")
	}
	if password == "" {
		return nil, errors.New("password is required")
	}
	if u, _ := s.repo.GetByUsername(username); u != nil {
		return nil, errors.New("username exists")
	}
	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return nil, err
	}
	u := &model.User{
		Username:       username,
		PasswordHash:   string(hash),
		Email:          email,
		Role:           requestedRole,
		RequestedRole:  requestedRole,
		Department:     department,
		ApprovalStatus: "pending",
	}
	if err := s.repo.CreateUser(u); err != nil {
		return nil, err
	}
	return u, nil
}

func (s *AuthService) Authenticate(username, password string) (*model.User, error) {
	u, err := s.repo.GetByUsername(username)
	if err != nil || u == nil {
		return nil, errors.New("invalid credentials")
	}
	switch u.ApprovalStatus {
	case "", "approved":
	default:
		if u.ApprovalStatus == "pending" {
			return nil, errors.New("account is pending approval")
		}
		return nil, errors.New("account is not approved")
	}
	if err := bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(password)); err != nil {
		return nil, errors.New("invalid credentials")
	}
	return u, nil
}

func (s *AuthService) IssueAccessToken(u *model.User, ttl time.Duration) (string, error) {
	claims := jwt.MapClaims{
		"sub":             u.ID,
		"name":            u.Username,
		"role":            u.Role,
		"approval_status": u.ApprovalStatus,
		"exp":             time.Now().Add(ttl).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(s.jwtSecret)
}

func (s *AuthService) CreateRefreshSession(userID int64, expiresAt time.Time) (string, error) {
	sess := &model.Session{UserID: userID, ExpiresAt: expiresAt}
	if err := s.repo.CreateSession(sess); err != nil {
		return "", err
	}
	return sess.ID, nil
}

func (s *AuthService) ValidateRefresh(id string) (*model.Session, error) {
	sess, err := s.repo.GetSessionByID(id)
	if err != nil || sess == nil {
		return nil, errors.New("invalid refresh token")
	}
	if time.Now().After(sess.ExpiresAt) {
		return nil, errors.New("refresh token expired")
	}
	return sess, nil
}

func (s *AuthService) GetUserByID(id int64) (*model.User, error) {
	return s.repo.GetByID(id)
}

func (s *AuthService) RevokeRefresh(id string) error { return s.repo.DeleteSession(id) }

func (s *AuthService) ListRegistrationRequests(status string) ([]model.User, error) {
	status = strings.TrimSpace(status)
	if status != "" && status != "all" && status != "pending" && status != "rejected" && status != "approved" {
		return nil, errors.New("invalid approval status")
	}
	return s.repo.ListRegistrationRequests(status)
}

func (s *AuthService) ApproveRegistration(id, approvedBy int64) error {
	if id <= 0 {
		return errors.New("invalid user id")
	}
	if approvedBy <= 0 {
		return errors.New("invalid approver")
	}
	return s.repo.ApproveRegistration(id, approvedBy)
}

func (s *AuthService) RejectRegistration(id, approvedBy int64, reason string) error {
	if id <= 0 {
		return errors.New("invalid user id")
	}
	if approvedBy <= 0 {
		return errors.New("invalid approver")
	}
	return s.repo.RejectRegistration(id, approvedBy, reason)
}

func normalizeRole(role string) string {
	switch strings.ToLower(strings.TrimSpace(role)) {
	case "admin":
		return "admin"
	case "employee":
		return "employee"
	default:
		return "guest"
	}
}
