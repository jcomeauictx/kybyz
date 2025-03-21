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
PYTHON ?= $(shell which python3 python python2 false | head -n 1)
PIP ?= $(shell which pip3 pip pip2 false | head -n 1)
PYLINT ?= $(shell which pylint3 pylint pylint2 true | head -n 1)
PY_VER := $(shell $(PYTHON) -c "import sys; print(sys.version_info[0])")
ifeq ($(PY_VER),3)
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
ONION_FILE := /tmp/kybyz.tor/hostname
ONION_ADDR = $(shell test -e $(ONION_FILE) && cat $(ONION_FILE))
EXTERNAL_PORT := 8008
ONION_URL := http://$(ONION_ADDR):$(EXTERNAL_PORT)
ifeq ($(SHOWENV),)
export APP KB_DELAY KB_WEB KB_LOGDIR KB_COMMS TMPDIR EXTERNAL_PORT USER_LOG
else
export
endif
all: $(PYLINT) doctests lint kybyz.conf kybyz.torrc uwsgi
%.doctest: %.py
	$(PYTHON) -m doctest $<
doctests: $(SOURCES:.py=.doctest)
%.lint %.pylint: %.py
	$(PYLINT) $<
lint pylint: $(SOURCES:.py=.lint)
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
uwsgi: kybyz.ini resources/vis-network.min.js
	#strace -f -v -t -s4096 -o $(TMPDIR)/kybyz_strace.log uwsgi $<
	# don't `2>&1`, it may affect prompt display
	uwsgi $<
nginx: $(PWD)/kybyz.conf
	nginx -c $< -e stderr &
nginx.stop:
	if [ -e /tmp/nginx_kybyz.pid ]; then \
	 if [ "$$(</tmp/nginx_kybyz.pid)" ]; then \
	  kill $$(</tmp/nginx_kybyz.pid); \
	 else \
	  echo 'found nginx pidfile empty' >&2; \
	 fi; \
	 rm -f /tmp/nginx_kybyz.pid; \
	else \
	 echo 'nginx already not running' >&2; \
	fi
tor: kybyz.torrc
	tor -f $< &
tor.stop:
	if [ -e /tmp/tor_kybyz.pid ]; then \
	 if [ "$$(</tmp/tor_kybyz.pid)" ]; then \
	  kill $$(</tmp/tor_kybyz.pid); \
	 else \
	  echo 'found tor pidfile empty' >&2; \
	 fi; \
	 rm -f /tmp/tor_kybyz.pid; \
	else \
	 echo 'tor already not running' >&2; \
	fi
stop:
	if [ -e /tmp/kybyz.pid ]; then \
	 if [ "$$(</tmp/kybyz.pid)" ]; then \
	  kill $$(</tmp/kybyz.pid); \
	 else \
	  echo 'found kybyz pidfile empty' >&2; \
	 fi; \
	 rm -f /tmp/kybyz.pid; \
	else \
	 echo 'kybyz already not running' >&2; \
	fi
strace:
	if [ -e /tmp/kybyz.pid ]; then \
	 strace -p $$(</tmp/kybyz.pid) \
	  -f -v -s128 -o '| tee /tmp/kybyz_strace.log'; \
	else \
	 echo cannot find pid of kybyz process >&2; \
	fi
$(USER_BIN):
	mkdir -p $@
$(PYLINT): $(USER_BIN)
	# assuming either pylint3 or pylint available
	command -v $(PYLINT) || \
	ln -s $$(command -v pylint3 || command -v pylint) $</$@
env:
ifeq ($(SHOWENV),)
	make SHOWENV=1 $@
else
	$@
endif
edit: k*.py
	vi $+
torview:
	torbrowser-launcher $(ONION_URL)
kybyz.service: service.template
	envsubst < $< > $@
kybyz.conf: nginx.conf.template
	envsubst < $< > $@
kybyz.torrc: kybyz.torrc.template linux.mk
	envsubst < $< > $@
push:
	git push -u origin master
	git push githost master
resources/vis-network.min.js:
	cd $(@D) && \
	 wget https://unpkg.com/vis-network/standalone/umd/$(@F)
