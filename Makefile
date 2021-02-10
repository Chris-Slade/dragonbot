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
	$(ENV) heroku local

tags: $(SRC)
	ctags $(SRC)

deploy:
	git push heroku master

stop:
	heroku ps:scale worker=0

start:
	heroku ps:scale worker=1

logs:
	heroku logs
