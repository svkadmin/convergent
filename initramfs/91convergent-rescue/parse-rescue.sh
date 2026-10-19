#!/bin/sh

[ "$(getarg convergent.rescue=)" = 1 ] || die 'rescue: missing rescue flag'
root=convergent-rescue
rootok=1
