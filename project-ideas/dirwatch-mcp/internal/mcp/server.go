package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	mcpgo "github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"github.com/learn-patwari/dirwatch-mcp/internal/actions"
	"github.com/learn-patwari/dirwatch-mcp/internal/config"
	"github.com/learn-patwari/dirwatch-mcp/internal/watcher"
)

type State struct {
	mu        sync.Mutex
	cfg       *config.Config
	cfgPath   string
	w         *watcher.Watcher
	lastEvent string
}

func NewState(cfgPath string) *State {
	s := &State{cfgPath: cfgPath}
	// try to load existing config; ignore errors
	cfg, err := config.Load(cfgPath)
	if err == nil {
		s.cfg = cfg
	}
	return s
}

func (s *State) handler(path string) {
	s.mu.Lock()
	cfg := s.cfg
	s.lastEvent = fmt.Sprintf("%s at %s", path, time.Now().UTC().Format(time.RFC3339))
	s.mu.Unlock()

	if cfg == nil {
		return
	}
	u := actions.NewUploader(cfg.APIKey, cfg.APIBaseURL, cfg.Project, cfg.Action.OnConflict)
	if err := u.Upload(cfg.WatchPath, path); err != nil {
		fmt.Printf("upload error: %v\n", err)
	}
}

func Build(s *State) *server.MCPServer {
	srv := server.NewMCPServer("dirwatch-mcp", "1.0.0")

	// list_projects
	srv.AddTool(mcpgo.NewTool("list_projects",
		mcpgo.WithDescription("Fetch available projects from the API"),
		mcpgo.WithString("apikey", mcpgo.Required(), mcpgo.Description("Bearer token")),
		mcpgo.WithString("api_base_url", mcpgo.Required(), mcpgo.Description("Base URL of the API")),
	), func(ctx context.Context, req mcpgo.CallToolRequest) (*mcpgo.CallToolResult, error) {
		apiKey, _ := req.Params.Arguments["apikey"].(string)
		baseURL, _ := req.Params.Arguments["api_base_url"].(string)

		httpReq, err := http.NewRequestWithContext(ctx, http.MethodGet, baseURL+"/projects", nil)
		if err != nil {
			return mcpgo.NewToolResultError(err.Error()), nil
		}
		httpReq.Header.Set("Authorization", "Bearer "+apiKey)
		httpReq.Header.Set("Accept", "application/json")

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Do(httpReq)
		if err != nil {
			return mcpgo.NewToolResultError(fmt.Sprintf("request failed: %v", err)), nil
		}
		defer resp.Body.Close()

		var projects []map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&projects); err != nil {
			return mcpgo.NewToolResultError(fmt.Sprintf("decode response: %v", err)), nil
		}

		out, _ := json.MarshalIndent(projects, "", "  ")
		return mcpgo.NewToolResultText(string(out)), nil
	})

	// set_config
	srv.AddTool(mcpgo.NewTool("set_config",
		mcpgo.WithDescription("Save configuration and (re)start the watcher"),
		mcpgo.WithString("apikey", mcpgo.Required(), mcpgo.Description("Bearer token")),
		mcpgo.WithString("api_base_url", mcpgo.Required(), mcpgo.Description("Base URL of the API")),
		mcpgo.WithString("project", mcpgo.Required(), mcpgo.Description("Project identifier")),
		mcpgo.WithString("watch_path", mcpgo.Required(), mcpgo.Description("Absolute path to watch")),
		mcpgo.WithString("action_type", mcpgo.Description("Action type (default: upload_file)")),
	), func(ctx context.Context, req mcpgo.CallToolRequest) (*mcpgo.CallToolResult, error) {
		s.mu.Lock()
		defer s.mu.Unlock()

		actionType, _ := req.Params.Arguments["action_type"].(string)
		if actionType == "" {
			actionType = "upload_file"
		}

		newCfg := &config.Config{
			APIKey:     req.Params.Arguments["apikey"].(string),
			APIBaseURL: req.Params.Arguments["api_base_url"].(string),
			Project:    req.Params.Arguments["project"].(string),
			WatchPath:  req.Params.Arguments["watch_path"].(string),
			Action: config.Action{
				Type:       actionType,
				OnConflict: "skip",
			},
		}

		if err := newCfg.Validate(); err != nil {
			return mcpgo.NewToolResultError(fmt.Sprintf("invalid config: %v", err)), nil
		}
		if err := config.Save(s.cfgPath, newCfg); err != nil {
			return mcpgo.NewToolResultError(fmt.Sprintf("save config: %v", err)), nil
		}

		if s.w != nil {
			s.w.Stop()
		}
		s.cfg = newCfg
		s.w = watcher.New(newCfg.WatchPath, newCfg.Action.IncludeHidden, newCfg.Action.Recursive, s.handler)
		if err := s.w.Start(); err != nil {
			return mcpgo.NewToolResultError(fmt.Sprintf("start watcher: %v", err)), nil
		}

		return mcpgo.NewToolResultText(fmt.Sprintf("configured: watching %s → project %s", newCfg.WatchPath, newCfg.Project)), nil
	})

	// watch_start
	srv.AddTool(mcpgo.NewTool("watch_start",
		mcpgo.WithDescription("Begin watching the configured path (idempotent)"),
	), func(ctx context.Context, req mcpgo.CallToolRequest) (*mcpgo.CallToolResult, error) {
		s.mu.Lock()
		defer s.mu.Unlock()

		if s.cfg == nil {
			return mcpgo.NewToolResultError("no configuration — call set_config first"), nil
		}
		if s.w == nil {
			s.w = watcher.New(s.cfg.WatchPath, s.cfg.Action.IncludeHidden, s.cfg.Action.Recursive, s.handler)
		}
		if err := s.w.Start(); err != nil {
			return mcpgo.NewToolResultError(err.Error()), nil
		}
		return mcpgo.NewToolResultText("watching " + s.cfg.WatchPath), nil
	})

	// watch_stop
	srv.AddTool(mcpgo.NewTool("watch_stop",
		mcpgo.WithDescription("Pause watching (config preserved)"),
	), func(ctx context.Context, req mcpgo.CallToolRequest) (*mcpgo.CallToolResult, error) {
		s.mu.Lock()
		defer s.mu.Unlock()

		if s.w != nil {
			s.w.Stop()
		}
		return mcpgo.NewToolResultText("watcher stopped"), nil
	})

	// get_status
	srv.AddTool(mcpgo.NewTool("get_status",
		mcpgo.WithDescription("Return current watcher state"),
	), func(ctx context.Context, req mcpgo.CallToolRequest) (*mcpgo.CallToolResult, error) {
		s.mu.Lock()
		defer s.mu.Unlock()

		type Status struct {
			Watching  bool   `json:"watching"`
			WatchPath string `json:"watch_path,omitempty"`
			Project   string `json:"project,omitempty"`
			LastEvent string `json:"last_event,omitempty"`
		}
		st := Status{}
		if s.w != nil {
			st.Watching = s.w.Running()
		}
		if s.cfg != nil {
			st.WatchPath = s.cfg.WatchPath
			st.Project = s.cfg.Project
		}
		st.LastEvent = s.lastEvent

		out, _ := json.MarshalIndent(st, "", "  ")
		return mcpgo.NewToolResultText(string(out)), nil
	})

	return srv
}
