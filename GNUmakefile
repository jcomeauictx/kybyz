# Has precedence over Makefile. Used for building and testing kybyz version 1
SOURCES := kybyz1.py
PYTHON ?= python3
PYLINT ?= pylint3
export
all: doctests lint uwsgi
%.doctest: %.py
	$(PYTHON) -m doctest $<
doctests: $(SOURCES:.py=.doctest)
%.lint: %.py $(PYLINT)
	$(PYLINT) $<
lint: $(SOURCES:.py=.lint)
uwsgi: kybyz1.ini
	uwsgi $<
$(PYLINT):
	which $@ || sudo apt-get install $@
	# for Debian Bullseye, no more pylint3
	which pylint  # fails if no pylint either
	which $@ || ln -sf $$(which pylint) $(HOME)/bin/$@
	# progressively worse (more global) locations
	which $@ || sudo ln -sf $$(which pylint) /usr/local/bin/$@
	which $@ || sudo ln -sf $$(which pylint) /usr/bin/$@
env:
	$@
