#!/bin/sh
if [ "$#" -eq 1 ]; then stdinmsg=$(cat); fi
exec <"$0" || exit; read v; read v; read v; exec /usr/bin/osascript - "$@" "$stdinmsg"; exit

on run {phoneNumber, message}
    activate application "Messages"
    tell application "System Events" to tell process "Messages"
        key code 45 using command down -- press Command + N to start a new window
        keystroke phoneNumber -- input the phone number
        key code 36 -- press Enter to focus on the message area
        keystroke message -- type some message
        key code 36 -- press Enter to send
    end tell
end run