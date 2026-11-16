#!/bin/sh
set -eu
: "${STUDIO_AUTH_USER:?STUDIO_AUTH_USER must be configured}"
: "${STUDIO_AUTH_PASSWORD:?STUDIO_AUTH_PASSWORD must be configured}"
umask 077
htpasswd -bc /etc/nginx/.voice-studio-htpasswd "$STUDIO_AUTH_USER" "$STUDIO_AUTH_PASSWORD" >/dev/null
exec nginx -g "daemon off;"
