package service

import (
	"strings"

	"github.com/golang-jwt/jwt/v5"
)

func ParseToken(bearer string, secret []byte) (map[string]interface{}, bool) {
	if strings.HasPrefix(bearer, "Bearer ") {
		bearer = bearer[len("Bearer "):]
	}
	t, err := jwt.Parse(bearer, func(token *jwt.Token) (interface{}, error) { return secret, nil })
	if err != nil || !t.Valid { return nil, false }
	if claims, ok := t.Claims.(jwt.MapClaims); ok {
		m := map[string]interface{}{}
		for k, v := range claims { m[k] = v }
		return m, true
	}
	return nil, false
}
