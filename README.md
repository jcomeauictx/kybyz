# kybyz
a peer to peer collaboration and social media platform

## quickstart

Install and test on a <https://digitalocean.com> Debian-11 droplet, the cheapest
one, currently $6/month.

**NOTE** if these instructions do not work, revert to the same version
as the README. You will be missing the latest functionality, but the steps have
a better chance of working correctly. I don't test the installation often.

1. Login as root
2. `apt update`
3. `apt upgrade`
4. `apt install make git xauth`
5. `adduser tester`
6. `usermod -a -G sudo tester`  \# will be `sudoers` on some systems
7. `mkdir ~tester/.ssh`
9. `cp ~/.ssh/authorized_keys ~tester/.ssh/`
10. `chown -R tester.tester ~tester/.ssh`

That's all as root; you should now login as a regular user

1. Login as tester; use `ssh -X` to tunnel Xwindows to your local box
2. Set `KB_USERNAME=myusername` and `KB_EMAIL=myemail@example.com`, replacing `myusername` and `myemail@example.com` with your own, hopefully unique, username and your real email address.
3. `gpg --pinentry-mode loopback --quick-gen-key "$KB_USERNAME <$KB_EMAIL>"` \# **just hit the enter key at the `Passphrase:` prompt**
4. `mkdir -p src`
5. `cd src`
6. `git clone https://github.com/jcomeauictx/kybyz`
7. `cd kybyz`
8. `sudo make install && make install`
9. `./kybyz.py register $KB_USERNAME $KB_EMAIL`
10. `make` \# Wait until the browser launches and you see a cat netmeme. There should be a `kbz>` prompt. If not, wait a few seconds and hit the enter key, and it should appear. **If pylint fails**, you can still test the app using `make PYLINT=echo`
11. \# Wait for the `kbz>` prompt
12. \# `send myusername myemail@example.com this is a private message` \# remember to use your actual kybyz username and email
13. \# Watch the log messages and make sure it was sent and received correctly.
14. \# Send to another user. First you'll need to import their public GPG key.
15. \# Login to Facebook and visit <https://www.facebook.com/jcomeauictx/about_contact_and_basic_info>. Copy my PGP key.
16. \# ^C out of kybyz on the droplet, and at the command line: `cat > /tmp/jc.key`.
17. \# Paste the key by clicking the middle mouse button (or both left and right if there is no middle).
18. \# ^D to get back to the command line.
19. \# `gpg --import /tmp/jc.key`
20. \# `gpg --sign-key jc@unternet.net`
21. \# `make`
22. \# At the `kbz>` prompt: `send jcomeauictx jc@unternet.net hey this is Joe`

I'll be able to read your message, but won't be able to verify who it's from
unless I have imported *your* key.

## troubleshooting

Testing while chrooting to different debootstrapped systems reveals some
problems. I already mentioned pylint: if the version is too old, it will
complain about many non-problems in the code. For that, just set 
PYLINT=echo preceding the `make` command.

If the version of gpg is too old, it will create empty
`$HOME/.gnupg/secring.gpg` and `$HOME/.gnupg/pubring.gpg` files and break your
current gpg setup. In that case:

 * Remove those two files
 * `mkdir -m 0700 $HOME/.gnupg_v1`
 * Make sure /usr/local/bin precedes /usr/bin in your PATH;
   You can fix this in your `$HOME/.bashrc` or `.bash_aliases` files.
 * Create, with mode 755, a file `/usr/local/bin/gpg` with the following
   contents:
   ```bash
   #!/bin/bash
   /usr/bin/gpg --homedir $HOME/.gnupg_v1 "$@"
   ```
 * `gpg --gen-key`, and follow the prompts.

If you're helping alpha test, each day before running the script you should
`git pull`. This brings in any code changes since the previous attempt.

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
* gpg
