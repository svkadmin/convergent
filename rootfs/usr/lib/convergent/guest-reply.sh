#!/bin/sh
# Never load an unbounded or incomplete guest reply into the shell.
guest_reply() (
    # Only display callers may keep failed replies.
    reply_display=0
    if [ "$1" = --display ]; then reply_display=1; shift; fi
    reply_limit=$1; shift
    umask 077
    # Root scratches in its own /run/convergent: an owner filling /tmp must not make replies look hostile.
    reply_tmp=${TMPDIR:-/tmp}
    [ "$(id -u)" != 0 ] || [ ! -d /run/convergent ] || reply_tmp=/run/convergent
    # A local scratch failure is no answer (1), never a rejected one (125).
    reply_dir=$(mktemp -d "$reply_tmp/guest-reply.XXXXXX") || exit 1
    trap 'rm -rf "$reply_dir"' 0
    trap 'exit 125' HUP INT TERM
    { reply_rc=0; "$@" || reply_rc=$?; printf '%s\n' "$reply_rc" >"$reply_dir/status"; } |
        head -c "$((reply_limit + 1))" >"$reply_dir/data" || exit 1
    [ "$(wc -c <"$reply_dir/data")" -le "$reply_limit" ] || exit 125
    [ -s "$reply_dir/status" ] || exit 1
    reply_rc=$(cat "$reply_dir/status")
    if [ "$reply_rc" != 0 ] && [ "$reply_display" = 0 ]; then
        # 125 distinguishes a rejected answer from an unanswered probe.
        [ ! -s "$reply_dir/data" ] || exit 125
        exit "$reply_rc"
    fi
    cat "$reply_dir/data" || exit 125
    exit "$reply_rc"
)
# Guest text for the owner's terminal: no control bytes but newline and tab (escapes, OSC 52).
guest_text() { tr -d '\000-\010\013-\037\177'; }
# Remote stderr bounded (64 KiB) and through guest_text; stdout and the status stay as they are.
guest_stderr() {
    { _guest_rc=$({ { _guest_rc=0; "$@" 2>&1 >&3 3>&- 4>&- || _guest_rc=$?; printf '%s\n' "$_guest_rc" >&4; } | head -c 65536 | guest_text >&2; } 4>&1); } 3>&1
    return "${_guest_rc:-1}"
}
