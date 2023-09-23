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
3. `gpg --pinentry-mode loopback --quick-gen-key "$KB_USERNAME <$KB_EMAIL>" rsa3072 default never` \# **just hit the enter key at the `Passphrase:` prompt**
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
91U/dvwAttkLNo/RHyF/
=r0hu
-----END PGP PUBLIC KEY BLOCK-----
```
