package mysqlrepo

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"

	"auth-service/internal/model"
	"github.com/google/uuid"
)

type UserRepository struct {
	db *sql.DB
}

func NewUserRepository(db *sql.DB) *UserRepository { return &UserRepository{db: db} }

func (r *UserRepository) EnsureSchema() error {
	statements := []string{
		`CREATE TABLE IF NOT EXISTS users (
			id BIGINT AUTO_INCREMENT PRIMARY KEY,
			username VARCHAR(50) NOT NULL UNIQUE,
			password_hash VARCHAR(255) NOT NULL,
			email VARCHAR(100) NULL,
			role ENUM('guest','employee','admin') NOT NULL DEFAULT 'guest',
			department VARCHAR(100) NULL,
			managed_strategies JSON NULL,
			requested_role ENUM('guest','employee','admin') NOT NULL DEFAULT 'guest',
			approval_status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'approved',
			approved_by BIGINT NULL,
			approved_at DATETIME NULL,
			rejected_reason VARCHAR(255) NULL,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`,
		`CREATE TABLE IF NOT EXISTS user_sessions (
			id VARCHAR(100) PRIMARY KEY,
			user_id BIGINT NOT NULL,
			ip_address VARCHAR(45) NOT NULL,
			user_agent TEXT NOT NULL,
			expires_at DATETIME NOT NULL,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`,
	}
	for _, statement := range statements {
		if _, err := r.db.Exec(statement); err != nil {
			return err
		}
	}

	columns := map[string]string{
		"requested_role":  "ENUM('guest','employee','admin') NOT NULL DEFAULT 'guest'",
		"approval_status": "ENUM('pending','approved','rejected') NOT NULL DEFAULT 'approved'",
		"approved_by":     "BIGINT NULL",
		"approved_at":     "DATETIME NULL",
		"rejected_reason": "VARCHAR(255) NULL",
	}
	for name, definition := range columns {
		if err := r.addColumnIfMissing("users", name, definition); err != nil {
			return err
		}
	}

	_, _ = r.db.Exec(`UPDATE users SET requested_role = role WHERE requested_role IS NULL OR requested_role = ''`)
	_, _ = r.db.Exec(`UPDATE users SET approval_status = 'approved' WHERE approval_status IS NULL OR approval_status = ''`)
	return nil
}

func (r *UserRepository) addColumnIfMissing(table, column, definition string) error {
	var exists int
	err := r.db.QueryRow(`
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
	_, err = r.db.Exec(fmt.Sprintf("ALTER TABLE %s ADD COLUMN %s %s", table, column, definition))
	return err
}

func (r *UserRepository) CreateUser(u *model.User) error {
	if strings.TrimSpace(u.RequestedRole) == "" {
		u.RequestedRole = u.Role
	}
	if strings.TrimSpace(u.ApprovalStatus) == "" {
		u.ApprovalStatus = "pending"
	}
	res, err := r.db.Exec(`
		INSERT INTO users
			(username,password_hash,email,role,department,requested_role,approval_status,approved_by,approved_at,rejected_reason)
		VALUES (?,?,?,?,?,?,?,?,?,?)`,
		u.Username,
		u.PasswordHash,
		u.Email,
		u.Role,
		u.Department,
		u.RequestedRole,
		u.ApprovalStatus,
		u.ApprovedBy,
		u.ApprovedAt,
		u.RejectedReason,
	)
	if err != nil {
		return err
	}
	id, err := res.LastInsertId()
	if err == nil {
		u.ID = id
	}
	return nil
}

func (r *UserRepository) GetByUsername(username string) (*model.User, error) {
	row := r.db.QueryRow(`SELECT
		id,username,password_hash,email,role,department,requested_role,approval_status,approved_by,approved_at,rejected_reason,created_at
		FROM users WHERE username=?`, username)
	u, err := scanUser(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return u, nil
}

func (r *UserRepository) GetByID(id int64) (*model.User, error) {
	row := r.db.QueryRow(`SELECT
		id,username,password_hash,email,role,department,requested_role,approval_status,approved_by,approved_at,rejected_reason,created_at
		FROM users WHERE id=?`, id)
	u, err := scanUser(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return u, nil
}

func (r *UserRepository) ListRegistrationRequests(status string) ([]model.User, error) {
	args := []interface{}{}
	where := "approval_status IN ('pending','rejected')"
	if strings.TrimSpace(status) != "" && status != "all" {
		where = "approval_status = ?"
		args = append(args, status)
	}
	rows, err := r.db.Query(`SELECT
		id,username,password_hash,email,role,department,requested_role,approval_status,approved_by,approved_at,rejected_reason,created_at
		FROM users
		WHERE `+where+`
		ORDER BY created_at DESC, id DESC`, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	users := []model.User{}
	for rows.Next() {
		u, err := scanUser(rows)
		if err != nil {
			return nil, err
		}
		users = append(users, *u)
	}
	return users, rows.Err()
}

func (r *UserRepository) ApproveRegistration(id, approvedBy int64) error {
	res, err := r.db.Exec(`
		UPDATE users
		SET approval_status='approved', role=requested_role, approved_by=?, approved_at=NOW(), rejected_reason=NULL
		WHERE id=? AND approval_status='pending'`, approvedBy, id)
	if err != nil {
		return err
	}
	affected, _ := res.RowsAffected()
	if affected == 0 {
		return sql.ErrNoRows
	}
	return nil
}

func (r *UserRepository) RejectRegistration(id, approvedBy int64, reason string) error {
	res, err := r.db.Exec(`
		UPDATE users
		SET approval_status='rejected', approved_by=?, approved_at=NOW(), rejected_reason=?
		WHERE id=? AND approval_status='pending'`, approvedBy, strings.TrimSpace(reason), id)
	if err != nil {
		return err
	}
	affected, _ := res.RowsAffected()
	if affected == 0 {
		return sql.ErrNoRows
	}
	return nil
}

type userScanner interface {
	Scan(dest ...interface{}) error
}

func scanUser(scanner userScanner) (*model.User, error) {
	u := &model.User{}
	var dept, rejectedReason sql.NullString
	var approvedBy sql.NullInt64
	var approvedAt sql.NullTime
	if err := scanner.Scan(
		&u.ID,
		&u.Username,
		&u.PasswordHash,
		&u.Email,
		&u.Role,
		&dept,
		&u.RequestedRole,
		&u.ApprovalStatus,
		&approvedBy,
		&approvedAt,
		&rejectedReason,
		&u.CreatedAt,
	); err != nil {
		return nil, err
	}
	if dept.Valid {
		s := dept.String
		u.Department = &s
	}
	if approvedBy.Valid {
		v := approvedBy.Int64
		u.ApprovedBy = &v
	}
	if approvedAt.Valid {
		t := approvedAt.Time
		u.ApprovedAt = &t
	}
	if rejectedReason.Valid {
		s := rejectedReason.String
		u.RejectedReason = &s
	}
	return u, nil
}

func (r *UserRepository) CreateSession(s *model.Session) error {
	if s.ID == "" {
		s.ID = uuid.NewString()
	}
	_, err := r.db.Exec(`INSERT INTO user_sessions (id,user_id,ip_address,user_agent,expires_at) VALUES (?,?,?,?,?)`, s.ID, s.UserID, "", "", s.ExpiresAt)
	return err
}

func (r *UserRepository) GetSessionByID(id string) (*model.Session, error) {
	row := r.db.QueryRow(`SELECT id,user_id,expires_at FROM user_sessions WHERE id=?`, id)
	s := &model.Session{}
	if err := row.Scan(&s.ID, &s.UserID, &s.ExpiresAt); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return s, nil
}

func (r *UserRepository) DeleteSession(id string) error {
	_, err := r.db.Exec(`DELETE FROM user_sessions WHERE id=?`, id)
	return err
}
