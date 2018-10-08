PY := python3.7
SRC := $(filter %.py, $(shell git ls-files))

.PHONY: compile test lint run tags deploy logs

compile:
	$(PY) -mpy_compile $(SRC)

test:
	cd src/ && $(PY) -m unittest discover -s ../test -v

lint:
	prospector

run:
	heroku local

tags: $(SRC)
	ctags $(SRC)

deploy:
	git push heroku master

logs:
	heroku logs
