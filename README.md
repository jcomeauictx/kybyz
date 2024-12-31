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
14. \# Send to another user. First you'll need to import their public GPG key (kybyzdotcom public key is below in this README; copy and paste it into a plain
text file, and name it kybyzdotcom.pub).
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

If you imported the expired kybyzdotcom public key (before 2024-12-29), you
should be able to get the new one using `gpg --refresh-keys`. It seemed to
work automagically for me, anyway. Then when signing with `gpg --sign-key`,
I had to use the entire 40-character ID, instead of "kybyzdotcom", to be
able to sign the new key:
`gpg --sign-key 341764CDFD52C18832E29A39110861CDBFA29713`

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
SnaMYEGiKugA
=LueN
-----END PGP PUBLIC KEY BLOCK-----
```
# developer notes

* Cloudflare, which is used (now, anyway) by ipfs.io, is returning 403
  "Forbidden" [errors on urllib requests](https://community.cloudflare.com/t/api-call-suddenly-returns-403-forbidden/396383). need to change useragent string.
  [fixed by commit 6903a329df]
* debugging messages are not shown in console window; the debug log is
  located at `$HOME/.local/log/kybyz.log`
* <https://uwsgi-docs.readthedocs.io/en/latest/WSGIquickstart.html>
