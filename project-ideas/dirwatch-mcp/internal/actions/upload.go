package actions

import (
	"bytes"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

const maxRetries = 3

type Uploader struct {
	APIKey     string
	APIBaseURL string
	Project    string
	OnConflict string
	client     *http.Client
}

func NewUploader(apiKey, apiBaseURL, project, onConflict string) *Uploader {
	return &Uploader{
		APIKey:     apiKey,
		APIBaseURL: apiBaseURL,
		Project:    project,
		OnConflict: onConflict,
		client:     &http.Client{Timeout: 30 * time.Second},
	}
}

func (u *Uploader) Upload(watchRoot, filePath string) error {
	rel, err := filepath.Rel(watchRoot, filePath)
	if err != nil {
		rel = filepath.Base(filePath)
	}

	data, err := os.ReadFile(filePath)
	if err != nil {
		return fmt.Errorf("read file: %w", err)
	}

	var lastErr error
	backoff := time.Second
	for attempt := 0; attempt <= maxRetries; attempt++ {
		if attempt > 0 {
			time.Sleep(backoff)
			backoff *= 2
		}

		status, err := u.doUpload(data, filepath.Base(filePath), rel)
		if err != nil {
			lastErr = err
			continue
		}

		if status == http.StatusCreated {
			return nil
		}
		if status == http.StatusConflict {
			if u.OnConflict == "overwrite" {
				_, err = u.doPut(data, filepath.Base(filePath), rel)
				if err == nil {
					return nil
				}
				lastErr = err
				continue
			}
			return nil // skip
		}
		lastErr = fmt.Errorf("unexpected status %d", status)
	}
	return fmt.Errorf("upload failed after %d attempts: %w", maxRetries, lastErr)
}

func (u *Uploader) doUpload(data []byte, filename, relPath string) (int, error) {
	body, contentType, err := buildMultipart(data, filename, relPath)
	if err != nil {
		return 0, err
	}
	url := fmt.Sprintf("%s/projects/%s/files", u.APIBaseURL, u.Project)
	req, err := http.NewRequest(http.MethodPost, url, body)
	if err != nil {
		return 0, err
	}
	req.Header.Set("Content-Type", contentType)
	req.Header.Set("Authorization", "Bearer "+u.APIKey)

	resp, err := u.client.Do(req)
	if err != nil {
		return 0, err
	}
	resp.Body.Close()
	return resp.StatusCode, nil
}

func (u *Uploader) doPut(data []byte, filename, relPath string) (int, error) {
	body, contentType, err := buildMultipart(data, filename, relPath)
	if err != nil {
		return 0, err
	}
	url := fmt.Sprintf("%s/projects/%s/files/%s", u.APIBaseURL, u.Project, filename)
	req, err := http.NewRequest(http.MethodPut, url, body)
	if err != nil {
		return 0, err
	}
	req.Header.Set("Content-Type", contentType)
	req.Header.Set("Authorization", "Bearer "+u.APIKey)

	resp, err := u.client.Do(req)
	if err != nil {
		return 0, err
	}
	resp.Body.Close()
	return resp.StatusCode, nil
}

func buildMultipart(data []byte, filename, relPath string) (io.Reader, string, error) {
	var buf bytes.Buffer
	w := multipart.NewWriter(&buf)

	fw, err := w.CreateFormFile("file", filename)
	if err != nil {
		return nil, "", err
	}
	fw.Write(data)

	w.WriteField("filename", filename)
	w.WriteField("rel_path", relPath)
	w.WriteField("added_at", time.Now().UTC().Format(time.RFC3339))
	w.Close()

	return &buf, w.FormDataContentType(), nil
}
