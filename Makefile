# set shell to Bash to allow use of bashisms in recipes
SHELL := /bin/bash
SOURCES ?= $(wildcard *.py)
PYTHON ?= python3
PYLINT ?= pylint3
# set KB_DELAY to smaller number for more frequent progress logging
KB_DELAY = 600
# set KB_LOGDIR to desired path
# it will be created by kbcommon.py at startup
KB_LOGDIR = $(HOME)/log
PATH := $(HOME)/bin:$(PATH)
export
all: doctests lint uwsgi
%.doctest: %.py
	$(PYTHON) -m doctest $<
doctests: $(SOURCES:.py=.doctest)
%.lint: %.py $(PYLINT)
	$(PYLINT) $<
lint: $(SOURCES:.py=.lint)
uwsgi: kybyz.ini
	#strace -f -v -t -s4096 -o /tmp/kybyz_strace.log uwsgi $<
	uwsgi $<
$(HOME)/bin:
	mkdir -p $@
$(PYLINT): $(HOME)/bin
	which $@ || sudo apt-get install $@
	# for Debian Bullseye, no more pylint3
	which $@ || which pylint # fails if no pylint either
	which $@ || ln -sf $$(which pylint) $(HOME)/bin/$@
	# progressively worse (more global) locations
	which $@ || sudo ln -sf $$(which pylint) /usr/local/bin/$@
	which $@ || sudo ln -sf $$(which pylint) /usr/bin/$@
env:
	$@
edit: k*.py
	vi $+
