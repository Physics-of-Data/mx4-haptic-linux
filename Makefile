BIN_DIR       := $(HOME)/.local/bin
AUTOSTART_DIR := $(HOME)/.config/autostart

# Managed files: "<repo source>|<installed target>"
# These pairs drive autostart/fetch/status. Keep in sync.
MANAGED := \
	"src/watch.py|$(BIN_DIR)/mx4-watch" \
	"src/demo.py|$(BIN_DIR)/mx4-demo" \
	"autostart/mx4-haptics.desktop|$(AUTOSTART_DIR)/mx4-haptics.desktop"

.PHONY: help deps run-watch run-demo autostart fetch status

help:
	@echo "Targets:"
	@echo "  deps        Create/sync the uv virtualenv (no runtime deps today)"
	@echo "  run-watch   Run src/watch.py under uv"
	@echo "  run-demo    Run src/demo.py under uv (LEVEL=N to pass --level N)"
	@echo "  autostart   Install scripts to ~/.local/bin and the autostart entry"
	@echo "  fetch       Copy installed files back over src/* and autostart/*"
	@echo "  status      Compare repo sources to installed copies"

deps:
	uv sync

run-watch:
	uv run src/watch.py

run-demo:
	uv run src/demo.py $(if $(LEVEL),--level $(LEVEL))

autostart:
	@install -d "$(BIN_DIR)" "$(AUTOSTART_DIR)"
	@for pair in $(MANAGED); do \
	    src=$${pair%%|*}; tgt=$${pair#*|}; \
	    case "$$tgt" in \
	        "$(BIN_DIR)"/*) mode=755 ;; \
	        *)              mode=644 ;; \
	    esac; \
	    install -m $$mode "$$src" "$$tgt"; \
	    echo "  install  $$src -> $$tgt"; \
	done

fetch:
	@for pair in $(MANAGED); do \
	    src=$${pair%%|*}; tgt=$${pair#*|}; \
	    if [ ! -f "$$tgt" ]; then \
	        echo "  skip    $$tgt (not installed)"; \
	    elif cmp -s "$$src" "$$tgt"; then \
	        echo "  same    $$tgt"; \
	    else \
	        cp "$$tgt" "$$src"; \
	        echo "  fetch   $$tgt -> $$src"; \
	    fi; \
	done

status:
	@for pair in $(MANAGED); do \
	    src=$${pair%%|*}; tgt=$${pair#*|}; \
	    if [ ! -f "$$tgt" ]; then \
	        printf "  %-12s %s\n" "[MISSING]" "$$tgt"; \
	    elif cmp -s "$$src" "$$tgt"; then \
	        printf "  %-12s %s\n" "[OK]" "$$src"; \
	    else \
	        src_mt=$$(stat -c %Y "$$src"); \
	        tgt_mt=$$(stat -c %Y "$$tgt"); \
	        if   [ "$$src_mt" -gt "$$tgt_mt" ]; then rel="src newer   -> deploy"; \
	        elif [ "$$tgt_mt" -gt "$$src_mt" ]; then rel="target newer -> fetch"; \
	        else                                       rel="same mtime, differ"; \
	        fi; \
	        printf "  %-12s %s  (%s)\n" "[DIFF]" "$$src" "$$rel"; \
	    fi; \
	done
