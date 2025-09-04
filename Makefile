
check:
	ruff check
	mypy --check-untyped-defs -p talkie
	pyright talkie/*

test:
	python -m pytest

format:
	ruff format

fix:
	ruff check --fix

