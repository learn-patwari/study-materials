package watcher

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestCreateEventFires(t *testing.T) {
	dir := t.TempDir()

	fired := make(chan string, 1)
	w := New(dir, false, false, func(path string) {
		fired <- path
	})
	if err := w.Start(); err != nil {
		t.Fatalf("start: %v", err)
	}
	defer w.Stop()

	target := filepath.Join(dir, "hello.txt")
	if err := os.WriteFile(target, []byte("hi"), 0644); err != nil {
		t.Fatalf("write: %v", err)
	}

	select {
	case got := <-fired:
		if got != target {
			t.Errorf("got %s, want %s", got, target)
		}
	case <-time.After(500 * time.Millisecond):
		t.Fatal("timed out waiting for event")
	}
}

func TestHiddenFilesSkipped(t *testing.T) {
	dir := t.TempDir()

	fired := make(chan string, 1)
	w := New(dir, false, false, func(path string) {
		fired <- path
	})
	if err := w.Start(); err != nil {
		t.Fatalf("start: %v", err)
	}
	defer w.Stop()

	os.WriteFile(filepath.Join(dir, ".hidden"), []byte("x"), 0644)

	select {
	case path := <-fired:
		t.Errorf("should not fire for hidden file, got %s", path)
	case <-time.After(300 * time.Millisecond):
		// expected
	}
}

func TestIdempotentStart(t *testing.T) {
	dir := t.TempDir()
	w := New(dir, false, false, func(string) {})
	if err := w.Start(); err != nil {
		t.Fatal(err)
	}
	if err := w.Start(); err != nil {
		t.Fatal("second Start should be idempotent")
	}
	w.Stop()
}
