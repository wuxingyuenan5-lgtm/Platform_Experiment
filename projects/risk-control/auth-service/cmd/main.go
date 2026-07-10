package main

import (
	"database/sql"
	"log"
	"net/http"
	"os"
	"time"

	"auth-service/internal/handler"
	"auth-service/internal/model"
	mysqlrepo "auth-service/internal/repository/mysql"
	"auth-service/internal/service"
	_ "github.com/go-sql-driver/mysql"
	"golang.org/x/crypto/bcrypt"
)

func main() {
	dsn := os.Getenv("DB_DSN")
	if dsn == "" {
		log.Fatal("DB_DSN environment variable is required")
	}
	jwtSecret := os.Getenv("JWT_SECRET")
	if jwtSecret == "" {
		log.Fatal("JWT_SECRET environment variable is required")
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	host := os.Getenv("HOST")
	if host == "" {
		host = "127.0.0.1"
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		log.Fatalf("failed opening db: %v", err)
	}
	defer db.Close()

	// simple ping
	db.SetConnMaxLifetime(time.Minute * 3)
	if err := db.Ping(); err != nil {
		log.Fatalf("db ping failed: %v", err)
	}

	userRepo := mysqlrepo.NewUserRepository(db)
	if err := userRepo.EnsureSchema(); err != nil {
		log.Fatalf("ensure schema failed: %v", err)
	}
	authSvc := service.NewAuthService(userRepo, []byte(jwtSecret))
	h := handler.NewAuthHandler(authSvc)

	// Optional: seed an admin user for development testing
	if os.Getenv("SEED_ADMIN") == "true" {
		seedName := os.Getenv("SEED_USERNAME")
		if seedName == "" {
			seedName = "admin"
		}
		seedPass := os.Getenv("SEED_PASSWORD")
		if seedPass == "" {
			log.Fatal("SEED_PASSWORD is required when SEED_ADMIN=true")
		}
		if u, _ := userRepo.GetByUsername(seedName); u == nil {
			hash, err := bcrypt.GenerateFromPassword([]byte(seedPass), bcrypt.DefaultCost)
			if err != nil {
				log.Printf("failed to hash seed password: %v", err)
			} else {
				now := time.Now()
				nu := &model.User{
					Username:       seedName,
					PasswordHash:   string(hash),
					Email:          "",
					Role:           "admin",
					RequestedRole:  "admin",
					ApprovalStatus: "approved",
					ApprovedAt:     &now,
				}
				if err := userRepo.CreateUser(nu); err != nil {
					log.Printf("seed user create failed: %v", err)
				} else {
					log.Printf("created seed user %s", seedName)
				}
			}
		} else {
			log.Printf("seed user %s already exists", seedName)
		}
	}

	// register routes
	h.HandleRoutes(http.DefaultServeMux)

	// simple CORS middleware to ease local development
	cors := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
			if r.Method == "OPTIONS" {
				w.WriteHeader(http.StatusNoContent)
				return
			}
			next.ServeHTTP(w, r)
		})
	}

	addr := host + ":" + port
	log.Printf("starting server on %s", addr)
	log.Fatal(http.ListenAndServe(addr, cors(http.DefaultServeMux)))
}
