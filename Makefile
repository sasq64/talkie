
check:
	ruff check
	mypy --check-untyped-defs -p talkie
	pyright talkie/*

mypy:
	mypy --check-untyped-defs -p talkie

test:
	python -m pytest

format:
	ruff format

fix:
	ruff check --fix

