# Has precedence over Makefile. Used for building and testing kybyz version 1
SOURCES := kybyz1.py
PYTHON ?= python3
PYLINT ?= pylint3
export
all: doctests pylint
%.doctest: %.py
	$(PYTHON) -m doctest $<
doctests: $(SOURCES:.py=.doctest)
%.pylint: %.py
	$(PYLINT) $<
pylint: $(SOURCES:.py=.pylint)
uwsgi: kybyz1.ini
	uwsgi $<
	
