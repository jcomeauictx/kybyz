ST := California
L := Petaluma
O := Unternet
E := hostmaster
OU := Tech
DRYRUN ?= --dry-run
localtest: kybyz.py
	python $<
client_test: localtest
	wget -O- --quiet http://kybyz:2424
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
$(HOME)/etc/kybyz:
	mkdir -p $@
keys:	$(HOME)/etc/kybyz
	$(MAKE) $</kybyz.crt
	$(MAKE) $</kybyz.public.pem
server_restart: ini
	sudo /etc/init.d/nginx restart
	sudo /etc/init.d/uwsgi restart
ini:
	cwd=$(PWD); for file in *.ini; do \
	 (cd /etc/uwsgi/apps-enabled && sudo ln -sf $$cwd/$$file .); \
	done
restart:
	sudo /etc/init.d/uwsgi stop
	killall --quiet --wait uwsgi || true
	uwsgi client.ini 2>>/tmp/kybyz.log &
	uwsgi example.ini 2>>/tmp/kybyz_example.log &
backup:
	for server in backup1 backup2; do \
	 rsync -avuz $(DRYRUN) --delete ~/.kybyz/ $$server:.kybyz/; \
	done