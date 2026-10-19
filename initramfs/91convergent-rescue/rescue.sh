#!/bin/sh

. /lib/convergent-unlock.sh
unset pass
mkdir -p "$state"
mount -t btrfs -o subvolid=5,noatime,nodev,nosuid,noexec /dev/mapper/cv-state "$state" ||
	die 'rescue: the state volume did not mount'
sh /sbin/convergent-rescue "$state"
# Never fall through to mounting or switching root.
die 'rescue: menu stopped'
