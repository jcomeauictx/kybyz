ST := California
L := Petaluma
O := Unternet
E := hostmaster
OU := Tech
DRYRUN ?= --dry-run
all: restart
localtest: kybyz.py
	python $<
client_test: localtest
	wget -O- --quiet http://kybyz0:2424
%.key: Makefile
	openssl genrsa -out $@ 1024
%.csr: %.key
	n=$(notdir $*) && \
	cn=www.$(notdir $*) && \
	openssl req -new -key $< -out $@ -subj \
	 /C=US/ST=$(ST)/L=$(L)/O=$(O)/OU=$(OU)/CN=$$cn/emailAddress=$(E)@$$n
%.crt: %.csr
	openssl x509 -req -days 365 -in $< -signkey $*.key -out $@
%.private.pem: Makefile
	openssl genrsa -out $@ 4096
	openssl rsa -text -in $@
%.public.pem: %.private.pem
	openssl rsa -pubout -in $< -out $@
	openssl rsa -text -pubin -in $@
.PRECIOUS: %.key %.csr %.private.pem
$(HOME)/etc/kybyz0:
	mkdir -p $@
keys:	$(HOME)/etc/kybyz0
	$(MAKE) $</kybyz.crt
	$(MAKE) $</kybyz.public.pem
$(USER)-kybyz.ini: client.ini.template
	envsubst < $< > $@
kybyz-example.ini: example.ini.template
	envsubst < $< > $@
ini: $(USER)-kybyz.ini kybyz-example.ini
	cwd=$(PWD); for file in $+; do \
	 (cd /etc/uwsgi/apps-enabled && sudo ln -sf $$cwd/$$file .); \
	done
restart: $(USER)-kybyz.ini $(HOME)/.kybyz_v0/favicon.ico
	uwsgi $<
backup:
	for server in backup1 backup2; do \
	 rsync -avuz $(DRYRUN) --delete ~/.kybyz/ $$server:.kybyz/; \
	done
%/favicon.ico: %
	convert -background none -fill green \
	 -size 128x128 -gravity center \
	 -font Helvetica label:k png:- | \
	 convert - -bordercolor white -border 0 \
	 \( -clone 0 -resize '16x16!' \) \
	 \( -clone 0 -resize '32x32!' \) \
	 \( -clone 0 -resize '48x48!' \) \
	 \( -clone 0 -resize '64x64!' \) \
   	 -delete 0 -alpha off -colors 256 -transparent white $@
%.pylint: %.py
	pylint $<
pylint: kybyz.pylint
%.doctest: %.py
	python3 -mdoctest --verbose $<
doctests: kybyz.doctest
.FORCE:
