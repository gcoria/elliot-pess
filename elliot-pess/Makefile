PY        ?= .venv/bin/python
PIP       ?= .venv/bin/pip
TICKER    ?= AAPL
FROM      ?= 2024-01-01
TO        ?= $(shell date +%Y-%m-%d)
CSV       ?= data/$(TICKER)_$(FROM)_$(TO).csv
DEVIATION ?= 0.03
TOP       ?= 3
PORT      ?= 8765
TOLERANCE ?= 0.015

.DEFAULT_GOAL := help
.PHONY: help install test fetch counts view analyze forecast forecast-csv clean

help:
	@echo "make install                         crea .venv e instala el paquete con extras dev y data"
	@echo "make test                            corre pytest"
	@echo "make fetch TICKER=AAPL FROM=2024-01-01 TO=2024-12-31"
	@echo "                                     baja velas diarias a $(CSV)"
	@echo "make counts [CSV=archivo.csv]        JSON con conteo primario y alternativas"
	@echo "make view   [CSV=archivo.csv]        abre el grafico con proyecciones"
	@echo "make analyze TICKER=... FROM=... TO=..."
	@echo "                                     fetch y despues view en un paso"
	@echo "make forecast TICKER=... FROM=... TO=..."
	@echo "                                     fetch y despues objetivo de la onda abierta, zonas y riesgo"
	@echo "make forecast-csv [CSV=archivo.csv]  lo mismo sobre un CSV que ya existe"
	@echo "make clean                           borra caches de Python y pytest"
	@echo ""
	@echo "Variables: TICKER FROM TO CSV DEVIATION TOP PORT TOLERANCE PY"

.venv/bin/python:
	python3 -m venv .venv

install: .venv/bin/python
	$(PIP) install -e ".[dev,data]"

test:
	$(PY) -m pytest -q

fetch:
	$(PY) -m elliot fetch $(TICKER) --from $(FROM) --to $(TO) --out $(CSV)

counts:
	$(PY) -m elliot counts $(CSV) --top $(TOP) --deviation $(DEVIATION) --json

view:
	$(PY) -m elliot view $(CSV) --top $(TOP) --deviation $(DEVIATION) --port $(PORT)

analyze: fetch view

forecast: fetch forecast-csv

forecast-csv:
	$(PY) -m elliot forecast $(CSV) --top $(TOP) --deviation $(DEVIATION) --tolerance $(TOLERANCE)

clean:
	find src tests -name "__pycache__" -type d -exec rm -rf {} +
	rm -rf .pytest_cache
