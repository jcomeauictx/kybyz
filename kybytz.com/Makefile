WEBSITE ?= $(notdir $(PWD))
DRYRUN ?= --dry-run
DOCROOT := /var/www/$(WEBSITE)
upload:
	rsync -avuz $(DRYRUN) $(DELETE) \
	 --exclude=Makefile \
	 --exclude=README.md \
	 . $(WEBSITE):$(DOCROOT)/

