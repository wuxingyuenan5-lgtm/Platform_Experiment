package utils

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func NewJWT(secret []byte, claims jwt.MapClaims, ttl time.Duration) (string, error) {
	claims["exp"] = time.Now().Add(ttl).Unix()
	t := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return t.SignedString(secret)
}
