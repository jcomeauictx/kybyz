# kybyz---a peer to peer collaboration and social media platform

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

# prerequisites

* python3
* python3-ecdsa
* python3-gnupg
