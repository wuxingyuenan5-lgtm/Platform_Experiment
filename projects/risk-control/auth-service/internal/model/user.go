package model

import "time"

type User struct {
	ID             int64      `db:"id" json:"id"`
	Username       string     `db:"username" json:"username"`
	PasswordHash   string     `db:"password_hash" json:"-"`
	Email          string     `db:"email" json:"email"`
	Role           string     `db:"role" json:"role"`
	Department     *string    `db:"department" json:"department,omitempty"`
	RequestedRole  string     `db:"requested_role" json:"requested_role"`
	ApprovalStatus string     `db:"approval_status" json:"approval_status"`
	ApprovedBy     *int64     `db:"approved_by" json:"approved_by,omitempty"`
	ApprovedAt     *time.Time `db:"approved_at" json:"approved_at,omitempty"`
	RejectedReason *string    `db:"rejected_reason" json:"rejected_reason,omitempty"`
	CreatedAt      time.Time  `db:"created_at" json:"created_at"`
}

type Session struct {
	ID        string    `db:"id" json:"id"`
	UserID    int64     `db:"user_id" json:"user_id"`
	ExpiresAt time.Time `db:"expires_at" json:"expires_at"`
}
