package scheduler

import (
	"context"
	"log"
	"time"
)

type SyncFunc func(context.Context) error

type Scheduler struct {
	interval time.Duration
	syncFunc SyncFunc
}

func New(interval time.Duration, _ bool, syncFunc SyncFunc) *Scheduler {
	return &Scheduler{
		interval: interval,
		syncFunc: syncFunc,
	}
}

func (s *Scheduler) Start(ctx context.Context) {
	if s == nil || s.syncFunc == nil || s.interval <= 0 {
		return
	}
	go func() {
		for {
			timer := time.NewTimer(time.Until(nextBoundary(time.Now(), s.interval)))
			select {
			case <-ctx.Done():
				timer.Stop()
				return
			case <-timer.C:
				s.runOnce(ctx)
			}
		}
	}()
}

func (s *Scheduler) runOnce(parent context.Context) {
	ctx, cancel := context.WithTimeout(parent, 45*time.Second)
	defer cancel()
	if err := s.syncFunc(ctx); err != nil {
		log.Printf("scheduled account net value snapshot failed: %v", err)
		return
	}
	log.Printf("scheduled account net value snapshot completed")
}

func nextBoundary(now time.Time, interval time.Duration) time.Time {
	next := now.Truncate(interval).Add(interval)
	if !next.After(now) {
		return now.Add(interval)
	}
	return next
}
