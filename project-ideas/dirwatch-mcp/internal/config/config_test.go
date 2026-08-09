package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")

	orig := &Config{
		APIKey:     "tok_test",
		APIBaseURL: "https://api.example.com",
		Project:    "proj_abc",
		WatchPath:  dir,
		Action: Action{
			Type:       "upload_file",
			OnConflict: "skip",
		},
	}

	if err := Save(path, orig); err != nil {
		t.Fatalf("save: %v", err)
	}

	got, err := Load(path)
	if err != nil {
		t.Fatalf("load: %v", err)
	}

	if got.APIKey != orig.APIKey || got.Project != orig.Project || got.WatchPath != orig.WatchPath {
		t.Errorf("round-trip mismatch: got %+v, want %+v", got, orig)
	}
}

func TestValidate(t *testing.T) {
	dir := t.TempDir()

	cfg := &Config{
		APIKey:     "tok",
		APIBaseURL: "https://x.com",
		Project:    "p",
		WatchPath:  dir,
	}
	if err := cfg.Validate(); err != nil {
		t.Errorf("expected valid: %v", err)
	}

	cfg.APIKey = ""
	if err := cfg.Validate(); err == nil {
		t.Error("expected error for missing apikey")
	}
	cfg.APIKey = "tok"

	cfg.WatchPath = filepath.Join(dir, "nonexistent")
	if err := cfg.Validate(); err == nil {
		t.Error("expected error for missing watch_path")
	}

	f, _ := os.CreateTemp(dir, "file")
	f.Close()
	cfg.WatchPath = f.Name()
	if err := cfg.Validate(); err == nil {
		t.Error("expected error when watch_path is a file")
	}
}
