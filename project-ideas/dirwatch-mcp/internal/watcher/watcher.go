package watcher

import (
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
)

const debounce = 100 * time.Millisecond

type Handler func(path string)

type Watcher struct {
	root          string
	includeHidden bool
	recursive     bool
	handler       Handler

	mu      sync.Mutex
	timers  map[string]*time.Timer
	fw      *fsnotify.Watcher
	done    chan struct{}
	running bool
}

func New(root string, includeHidden, recursive bool, handler Handler) *Watcher {
	return &Watcher{
		root:          root,
		includeHidden: includeHidden,
		recursive:     recursive,
		handler:       handler,
		timers:        make(map[string]*time.Timer),
	}
}

func (w *Watcher) Start() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.running {
		return nil
	}

	fw, err := fsnotify.NewWatcher()
	if err != nil {
		return err
	}
	if err := fw.Add(w.root); err != nil {
		fw.Close()
		return err
	}

	if w.recursive {
		_ = filepath.WalkDir(w.root, func(path string, d os.DirEntry, err error) error {
			if err == nil && d.IsDir() && path != w.root {
				fw.Add(path)
			}
			return nil
		})
	}

	w.fw = fw
	w.done = make(chan struct{})
	w.running = true
	go w.loop()
	return nil
}

func (w *Watcher) Stop() {
	w.mu.Lock()
	defer w.mu.Unlock()
	if !w.running {
		return
	}
	close(w.done)
	w.fw.Close()
	w.running = false
}

func (w *Watcher) Running() bool {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.running
}

func (w *Watcher) loop() {
	for {
		select {
		case <-w.done:
			return
		case event, ok := <-w.fw.Events:
			if !ok {
				return
			}
			if event.Op&fsnotify.Create == 0 {
				continue
			}
			info, err := os.Stat(event.Name)
			if err != nil {
				continue
			}
			if info.IsDir() {
				if w.recursive {
					w.fw.Add(event.Name)
				}
				continue
			}
			base := filepath.Base(event.Name)
			if !w.includeHidden && strings.HasPrefix(base, ".") {
				continue
			}
			w.debounce(event.Name)
		case err, ok := <-w.fw.Errors:
			if !ok {
				return
			}
			log.Printf("watcher error: %v", err)
		}
	}
}

func (w *Watcher) debounce(path string) {
	w.mu.Lock()
	defer w.mu.Unlock()
	if t, ok := w.timers[path]; ok {
		t.Reset(debounce)
		return
	}
	w.timers[path] = time.AfterFunc(debounce, func() {
		w.mu.Lock()
		delete(w.timers, path)
		w.mu.Unlock()
		w.handler(path)
	})
}
