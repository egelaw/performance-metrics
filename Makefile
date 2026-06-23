PYTHON ?= python

.PHONY: install test run

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

test:
	pytest -q

run:
	$(PYTHON) compare_timeseries.py /path/to/file.txt --observed-pattern "ObservedColumnName"
