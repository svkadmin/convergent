#!/bin/sh

. /lib/convergent-unlock.sh
unset pass
mkdir -p "$state"
# A volume whose log no longer replays still mounts read-only: the shell and the log copy work, writes do not.
if ! mount -t btrfs -o subvolid=5,noatime,nodev,nosuid,noexec /dev/mapper/cv-state "$state"; then
	mount -t btrfs -o ro,nologreplay,subvolid=5,nodev,nosuid,noexec /dev/mapper/cv-state "$state" ||
		die 'rescue: the state volume did not mount'
	echo 'rescue: the state volume mounted read-only (no log replay): copy the logs; writes will fail'
fi
sh /sbin/convergent-rescue "$state"
# Never fall through to mounting or switching root.
die 'rescue: menu stopped'
