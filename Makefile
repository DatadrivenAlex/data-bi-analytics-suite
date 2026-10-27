.PHONY: install test run docker

install:
	python -m pip install -e ".[dev]"

test:
	pytest

run:
	bi-analytics run

docker:
	docker compose up --build
