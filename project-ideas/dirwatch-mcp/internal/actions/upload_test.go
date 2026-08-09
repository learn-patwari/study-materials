package actions

import (
	"io"
	"mime"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestUploadSuccess(t *testing.T) {
	var gotAuth, gotFilename, gotRelPath string

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		mediaType, params, _ := mime.ParseMediaType(r.Header.Get("Content-Type"))
		if !strings.HasPrefix(mediaType, "multipart/") {
			t.Errorf("expected multipart, got %s", mediaType)
		}
		mr := multipart.NewReader(r.Body, params["boundary"])
		for {
			p, err := mr.NextPart()
			if err == io.EOF {
				break
			}
			data, _ := io.ReadAll(p)
			switch p.FormName() {
			case "filename":
				gotFilename = string(data)
			case "rel_path":
				gotRelPath = string(data)
			}
		}
		w.WriteHeader(http.StatusCreated)
	}))
	defer srv.Close()

	dir := t.TempDir()
	f := filepath.Join(dir, "test.txt")
	os.WriteFile(f, []byte("hello"), 0644)

	u := NewUploader("tok_test", srv.URL, "proj_abc", "skip")
	if err := u.Upload(dir, f); err != nil {
		t.Fatalf("upload: %v", err)
	}

	if gotAuth != "Bearer tok_test" {
		t.Errorf("auth header: got %q", gotAuth)
	}
	if gotFilename != "test.txt" {
		t.Errorf("filename: got %q", gotFilename)
	}
	if gotRelPath != "test.txt" {
		t.Errorf("rel_path: got %q", gotRelPath)
	}
}

func TestUploadConflictSkip(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusConflict)
	}))
	defer srv.Close()

	dir := t.TempDir()
	f := filepath.Join(dir, "dup.txt")
	os.WriteFile(f, []byte("x"), 0644)

	u := NewUploader("tok", srv.URL, "p", "skip")
	if err := u.Upload(dir, f); err != nil {
		t.Errorf("skip on conflict should not error: %v", err)
	}
}

func TestUploadRetry(t *testing.T) {
	attempts := 0
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attempts++
		if attempts < 3 {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusCreated)
	}))
	defer srv.Close()

	dir := t.TempDir()
	f := filepath.Join(dir, "retry.txt")
	os.WriteFile(f, []byte("y"), 0644)

	u := NewUploader("tok", srv.URL, "p", "skip")
	// speed up retry for test
	u.client.Timeout = 5 * time.Second
	if err := u.Upload(dir, f); err != nil {
		t.Errorf("should succeed after retries: %v", err)
	}
	if attempts != 3 {
		t.Errorf("expected 3 attempts, got %d", attempts)
	}
}
