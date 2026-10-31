# verify() from v0.1.4-rc1:rootfs/usr/lib/convergent/update.sh.
verify() { openssl pkeyutl -verify -pubin -inkey "$key" -rawin -in "$1" -sigfile "$1.sig" >/dev/null 2>&1; }
