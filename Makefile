.PHONY: venv install run validate build-linux

venv:
	python -m venv .venv

install:
	python -m pip install -r requirements.txt -r requirements-dev.txt

run:
	python -m pdf_tools

validate:
	python scripts/validate-metadata.py

build-linux:
	./scripts/linux/build-linux.sh
