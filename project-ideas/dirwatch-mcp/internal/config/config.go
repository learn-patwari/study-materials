package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type Action struct {
	Type          string `yaml:"type"`
	OnConflict    string `yaml:"on_conflict"`
	IncludeHidden bool   `yaml:"include_hidden"`
	Recursive     bool   `yaml:"recursive"`
}

type Config struct {
	APIKey     string `yaml:"apikey"`
	APIBaseURL string `yaml:"api_base_url"`
	Project    string `yaml:"project"`
	WatchPath  string `yaml:"watch_path"`
	Action     Action `yaml:"action"`
}

func DefaultPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".config", "dirwatch-mcp", "config.yaml")
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}
	return &cfg, nil
}

func Save(path string, cfg *Config) error {
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return err
	}
	data, err := yaml.Marshal(cfg)
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0600)
}

func (c *Config) Validate() error {
	if c.APIKey == "" {
		return fmt.Errorf("apikey is required")
	}
	if c.APIBaseURL == "" {
		return fmt.Errorf("api_base_url is required")
	}
	if c.Project == "" {
		return fmt.Errorf("project is required")
	}
	if c.WatchPath == "" {
		return fmt.Errorf("watch_path is required")
	}
	info, err := os.Stat(c.WatchPath)
	if err != nil {
		return fmt.Errorf("watch_path: %w", err)
	}
	if !info.IsDir() {
		return fmt.Errorf("watch_path is not a directory: %s", c.WatchPath)
	}
	return nil
}
