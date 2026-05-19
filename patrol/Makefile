.PHONY: install build run clean dev

# Variables
VENV = venv
PYTHON = python3
NPM = npm

install:
	$(PYTHON) -m pip install -r requirements.txt
	cd web && $(NPM) install

build: build-frontend

build-frontend:
	cd web && $(NPM) run build

run:
	$(PYTHON) app.py

dev:
	$(PYTHON) app.py

clean:
	rm -rf web/dist
	rm -rf __pycache__ core/__pycache__ plugins/__pycache__ notifiers/__pycache__
	rm -f patrol.db

all: install build
	@echo "Build complete. Run: make run"