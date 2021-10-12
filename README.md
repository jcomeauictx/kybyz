# kybyz
a peer to peer collaboration and social media platform

## quickstart
Install and test on a <https://digitalocean.com> Debian-11 droplet:
1. login as root
2. apt install firefox-esr python3 python3-pip pylint3 gpg xauth
3. apt install uwsgi uwsgi-plugin-python3
4. adduser tester
5. usermod -a -G sudo tester
6. mkdir ~tester/.ssh
7. cp ~/.ssh/authorized\_keys ~tester/.ssh/
8. chown -R tester.tester ~tester/.ssh

That's all as root; you should now login as a regular user

1. login as tester
2. gpg --pinentry-mode loopback --quick-gen-key "myusername \<myemail@example.com\>"
2. pip install gnupg
3. mkdir -p src
4. cd src
5. git clone https://github.com/jcomeauictx/kybyz
6. cd kybyz
7. make
8. at the kbz> prompt, type: register myusername myemail@example.com

It currently fails at this point. I upgraded my gnupg package to the latest and am troubleshooting the problems.


## proof of authorship

On a platform such as Facebook, proof of authorship is "automatic" in the sense
that, on a centralized platform, everyone has a unique ID protected by their
password. Of course, passwords can be guessed, phished, or otherwise obtained
by other people and thus can impersonate the author, but generally speaking,
if you see a post from jcomeauictx, you can assume I was the author.

On a peer to peer system it's a lot harder. We'll be using cryptographic
signatures with gpg (GNU's implementation of Pretty Good Privacy, PGP), but
you'll still have to get your public key out to the people you want in your
network.

## timestamping

In addition to proof of authorship, we will need to have a provable timestamp,
not just the falsifiable "timestamp" field currently in
example.kybyz/netmeme.json. See
<https://www.jamieweb.net/blog/proof-of-timestamp/> for some ideas on this; for
example, you can embed the hash of the post in a BCH transaction along with
the hash of the previous block. This proves the post is no older than the
previous block, and no newer than the transaction timestamp.

## prerequisites

* python3
* python3-ecdsa
* python3-gnupg
