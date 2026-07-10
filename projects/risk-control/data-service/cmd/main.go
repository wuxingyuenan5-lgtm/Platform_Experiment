package main

import (
	"context"
	"database/sql"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/go-sql-driver/mysql"

	"data-service/internal/config"
	"data-service/internal/handler"
	apiadapter "data-service/internal/repository/api"
	mysqlrepo "data-service/internal/repository/mysql"
	"data-service/internal/scheduler"
	"data-service/internal/service"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("load config failed: %v", err)
	}

	db, err := sql.Open("mysql", cfg.DBDSN)
	if err != nil {
		log.Fatalf("open db failed: %v", err)
	}
	defer db.Close()
	db.SetConnMaxLifetime(3 * time.Minute)
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	if err := db.Ping(); err != nil {
		log.Fatalf("db ping failed: %v", err)
	}

	repo := mysqlrepo.NewRepository(db)
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if cfg.AutoMigrate {
		if err := repo.EnsureSchema(ctx); err != nil {
			log.Fatalf("ensure schema failed: %v", err)
		}
	}

	bybitClient := apiadapter.NewBybitClient(cfg.Bybit, nil)
	dataSvc := service.NewDataService(cfg, repo, bybitClient)
	if cfg.SchedulerEnabled {
		s := scheduler.New(cfg.SyncInterval, cfg.SyncOnStart, func(ctx context.Context) error {
			_, err := dataSvc.RecordAccountNetValues(ctx)
			return err
		})
		s.Start(ctx)
		log.Printf("account net value scheduler enabled, interval=%s", cfg.SyncInterval)
	}

	mux := http.NewServeMux()
	handler.New(dataSvc).Register(mux)

	server := &http.Server{
		Addr:              cfg.Host + ":" + cfg.Port,
		Handler:           cors(mux),
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			log.Printf("server shutdown failed: %v", err)
		}
	}()

	log.Printf("starting data-service on :%s", cfg.Port)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server failed: %v", err)
	}
}

func cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, token")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
