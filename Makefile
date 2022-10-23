PY := python
SRC := $(filter %.py, $(shell git ls-files))
ENV := pipenv run

.PHONY: compile test lint run tags deploy logs

compile:
	$(PY) -mpy_compile $(SRC)

test:
	PYTHONPATH=src $(ENV) $(PY) -m unittest discover -s test -v

lint:
	$(ENV) prospector

run:
	$(ENV) python src/dragonbot.py

tags: $(SRC)
	ctags $(SRC)
