ST := California
L := Petaluma
O := Unternet
E := hostmaster
OU := Tech
localtest:
	wget -O- --quiet http://127.0.0.1:9090/
client_test:
	wget -O- --quiet --no-check-certificate https://kybyz/
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
restart: ini
	sudo /etc/init.d/nginx restart
	sudo /etc/init.d/uwsgi restart
ini:
	cwd=$(PWD); for file in *.ini; do \
	 (cd /etc/uwsgi/apps-enabled && sudo ln -sf $$cwd/$$file .); \
	done
