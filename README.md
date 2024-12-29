# kybyz
a peer to peer collaboration and social media platform

## quickstart

Install and test on a <https://digitalocean.com> Debian-11 droplet, the cheapest
one, currently $6/month.

**NOTE** if these instructions do not work, revert to the same version
as the README. You will be missing the latest functionality, but the steps have
a better chance of working correctly. I don't test the installation often.

1. Login as root
2. `apt update`  \# for CentOS, use `yum`
3. `apt upgrade`
4. `apt install make git xauth`  \# for CentOS, add `gcc`, `firefox`, and `python3-devel`
5. `adduser tester`
6. `usermod -a -G sudo tester`  \# will be `sudoers` on some systems
7. `mkdir ~tester/.ssh`
9. `cp ~/.ssh/authorized_keys ~tester/.ssh/`
10. `chown -R tester.tester ~tester/.ssh`

That's all as root; you should now login as a regular user

1. Login as tester; use `ssh -X` to tunnel Xwindows to your local box
2. Set `KB_USERNAME=myusername` and `KB_EMAIL=myemail@example.com`, replacing `myusername` and `myemail@example.com` with your own, hopefully unique, username and your real email address.
3. `gpg --default-new-key-algo "rsa3072/cert,sign+rsa3072/encr" --pinentry-mode loopback --quick-gen-key "$KB_USERNAME <$KB_EMAIL>" default default never` \# **just hit the enter key at the `Passphrase:` prompt**
4. `mkdir -p src`
5. `cd src`
6. `git clone https://github.com/jcomeauictx/kybyz`
7. `cd kybyz`
8. `cp Makefile.template Makefile`, and edit Makefile with your `KB_USERNAME` and `KB_EMAIL` values.
9. `sudo make install && make install`  \# on CentOs, `sudo make install` will fail and you'll need to `make install` separately.
10. `make` \# Wait until the browser launches and you see a cat netmeme. There should be a `kbz>` prompt. If not, wait a few seconds and hit the enter key, and it should appear. **If pylint fails**, you can still test the app using `make PYLINT=echo`
11. \# Wait for the `kbz>` prompt
12. \# `send myusername myemail@example.com this is a private message` \# remember to use your actual kybyz username and email
13. \# Watch the log messages and make sure it was sent and received correctly.
14. \# Send to another user. First you'll need to import their public GPG key (kybyzdotcom public key is below in this README).
15. \# ^C to get back to the command line.
16. `gpg --import kybyzdotcom.pub`
17. `gpg --sign-key kybyzdotcom`
18. `make`
19. \# At the `kbz>` prompt: `send kybyzdotcom kybyz@kybyz.com hey this is Joe`

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
network using `gpg --armor --export me@example.com | mail -s "my public key" myfriend@example.com`.

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

## notes on Android

It can run under Termux. Install from f-droid, not from the App Store.
You will need to install a number of packages, including `python`, `uwsgi`,
and many others I can't think of at the moment. And with `pip`, you will have
to get, at least, `pylint`.

Termux has the uwsgi package, but no plugin for Python, so we must build one.

1. `git clone https://github.com/jcomeauictx/uwsgi` at the Termux shell prompt,
and cd to the directory
2. Find what version of uwsgi you have; `uwsgi --version`. I had 2.0.20
3. Check out that version into its own branch:
   `git checkout tags/2.0.20 -bv2.0.20`
4. `PYTHON=python3 uwsgi --build-plugin "plugins/python python3"`
5. `cd ../kybyz`; and `ln -s ../uwsgi/python3_plugin.so .`
6. `make`

## kybyzdotcom public key

```gpg
-----BEGIN PGP PUBLIC KEY BLOCK-----

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
2suFs9pAPBZd
=Y6o6
-----END PGP PUBLIC KEY BLOCK-----
```
# developer notes

* Cloudflare, which is used (now, anyway) by ipfs.io, is returning 403
  "Forbidden" [errors on urllib requests](https://community.cloudflare.com/t/api-call-suddenly-returns-403-forbidden/396383). need to change useragent string.
