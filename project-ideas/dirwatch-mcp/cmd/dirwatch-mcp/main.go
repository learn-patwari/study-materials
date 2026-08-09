package main

import (
	"log"

	"github.com/mark3labs/mcp-go/server"

	"github.com/learn-patwari/dirwatch-mcp/internal/config"
	mcpsrv "github.com/learn-patwari/dirwatch-mcp/internal/mcp"
)

func main() {
	cfgPath := config.DefaultPath()
	state := mcpsrv.NewState(cfgPath)
	srv := mcpsrv.Build(state)

	if err := server.ServeStdio(srv); err != nil {
		log.Fatalf("mcp server error: %v", err)
	}
}
