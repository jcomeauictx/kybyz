WEBSITE ?= $(notdir $(PWD))
DRYRUN ?= --dry-run
DOCROOT := /var/www/$(WEBSITE)
upload:
	rsync -avuz $(DRYRUN) \
	 . root@$(WEBSITE):$(DOCROOT)/

