PY := python
SRC := $(filter %.py, $(shell git ls-files))

compile:
	$(PY) -mpy_compile $(SRC)

lint:
	prospector

tags: $(SRC)
	ctags $(SRC)

deploy:
	git push heroku master

logs:
	heroku logs
