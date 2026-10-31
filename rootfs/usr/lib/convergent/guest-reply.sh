#!/bin/sh
# Never load an unbounded or incomplete guest reply into the shell.
guest_reply() (
    # Only display callers may keep failed replies.
    reply_display=0
    if [ "$1" = --display ]; then reply_display=1; shift; fi
    reply_limit=$1; shift
    umask 077
    reply_dir=$(mktemp -d "${TMPDIR:-/tmp}/guest-reply.XXXXXX") || exit 125
    trap 'rm -rf "$reply_dir"' 0
    trap 'exit 125' HUP INT TERM
    { reply_rc=0; "$@" || reply_rc=$?; printf '%s\n' "$reply_rc" >"$reply_dir/status"; } |
        head -c "$((reply_limit + 1))" >"$reply_dir/data" || exit 125
    [ "$(wc -c <"$reply_dir/data")" -le "$reply_limit" ] && [ -s "$reply_dir/status" ] || exit 125
    reply_rc=$(cat "$reply_dir/status")
    if [ "$reply_rc" != 0 ] && [ "$reply_display" = 0 ]; then
        # 125 distinguishes a rejected answer from an unanswered probe.
        [ ! -s "$reply_dir/data" ] || exit 125
        exit "$reply_rc"
    fi
    cat "$reply_dir/data" || exit 125
    exit "$reply_rc"
)
