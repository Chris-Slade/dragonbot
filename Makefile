PY := python
SRC := $(filter %.py, $(shell git ls-files))
PYLINT_IGNORE :=       \
	missing-docstring  \
	bad-continuation   \
	wrong-import-order \
	logging-format-interpolation

compile:
	$(PY) -mpy_compile $(SRC)

lint:
	pylint $(SRC) --rcfile=pylint.rc $(foreach i, $(PYLINT_IGNORE), -d $i)

tags: $(SRC)
	ctags $(SRC)
