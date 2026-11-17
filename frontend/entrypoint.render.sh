#!/bin/sh
set -eu
: "${STUDIO_AUTH_USER:?STUDIO_AUTH_USER must be configured}"
: "${STUDIO_AUTH_PASSWORD:?STUDIO_AUTH_PASSWORD must be configured}"
umask 077
htpasswd -bc /etc/nginx/.voice-studio-htpasswd "$STUDIO_AUTH_USER" "$STUDIO_AUTH_PASSWORD" >/dev/null
# Nginx runs request workers as the 'nginx' user, not root.
# Keep the hash file private, but readable by that worker group.
chown root:nginx /etc/nginx/.voice-studio-htpasswd
chmod 0640 /etc/nginx/.voice-studio-htpasswd
exec nginx -g "daemon off;"
