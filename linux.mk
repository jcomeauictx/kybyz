# set shell to Bash to allow use of bashisms in recipes
# `make SHELL='/bin/bash -x'` to debug Makefile
SHELL := /bin/bash
APP := $(notdir $(PWD))
SOURCES ?= $(wildcard *.py)
INSTALLER ?= $(shell command -v yum || command -v apt-get || command -v echo)
REQUIRED := chromium gpg
PKG_REQUIRED := uwsgi-plugin-python3 python3-gnupg pylint3
PIP_REQUIRED := uwsgi python-gnupg pylint
USER_BIN ?= $(HOME)/.local/bin
USER_LOG ?= $(HOME)/.local/log
PY_VER := $(shell python -c "import sys; print(sys.version_info[0])")
ifeq ($(PY_VER),3)
 PYTHON ?= python
 PYLINT ?= pylint
 PIP ?= pip
else
 PYTHON ?= python3
 PYLINT ?= pylint3
 PIP ?= pip3
 REQUIRED += $(PKG_REQUIRED)
endif
# set KB_DELAY to smaller number for more frequent progress logging
KB_DELAY ?= 600
# set KB_LOGDIR to desired path
# it will be created by kbcommon.py at startup
KB_LOGDIR := $(USER_LOG)
PATH := $(USER_BIN):$(PATH)
# set fixed port of 26351 derived from base36 of 'kbz'
KB_WEB := $(shell $(PYTHON) -c "print(int('kbz', 36))")
KB_COMMS := $(shell expr $(KB_WEB) + 1)
TMPDIR := $(shell $(PYTHON) -c "import tempfile; print(tempfile.gettempdir())")
export
all: $(PYLINT) doctests lint uwsgi
%.doctest: %.py
	$(PYTHON) -m doctest $<
doctests: $(SOURCES:.py=.doctest)
%.lint: %.py
	$(PYLINT) $<
lint: $(SOURCES:.py=.lint)
install:  # run first as root, then as user
	if [ -w / ]; then \
	 $(INSTALLER) update; \
	 command -v python3 || command -v python || \
	 $(INSTALLER) install python3 || $(INSTALLER) install python; \
	 command -v pip3 || command -v pip || \
	 $(INSTALLER) install python3-pip || $(INSTALLER) install python-pip; \
	 $(INSTALLER) install $(REQUIRED); \
	else \
	 for package in $(PIP_REQUIRED); do \
	  command -v $$package || \
	  $(PYTHON) -c "import $${package##python-}" || \
	  $(PIP) install --user $$package; \
	 done; \
	fi  
uwsgi: kybyz.ini
	#strace -f -v -t -s4096 -o $(TMPDIR)/kybyz_strace.log uwsgi $<
	# redirection commented out, it may affect prompt display
	uwsgi $< #2>&1 | tee $(TMPDIR)/kybyz_uwsgi.log
$(USER_BIN):
	mkdir -p $@
$(PYLINT): $(USER_BIN)
	# assuming either pylint3 or pylint available
	command -v $(PYLINT) || \
	ln -s $$(command -v pylint3 || command -v pylint) $</$@
env:
	$@
edit: k*.py
	vi $+
kybyz.service: service.template
	envsubst < $< > $@
kybyz.conf: nginx.conf.template
	envsubst < $< > $@
kybyz.torrc: kybyz.torrc.template linux.mk
	envsubst < $< > $@
