#!/bin/sh
set -eu
: "${STUDIO_AUTH_USER:?STUDIO_AUTH_USER must be configured}"
: "${STUDIO_AUTH_PASSWORD:?STUDIO_AUTH_PASSWORD must be configured}"
umask 077
htpasswd -bc /etc/nginx/.voice-studio-htpasswd "$STUDIO_AUTH_USER" "$STUDIO_AUTH_PASSWORD" >/dev/null
# Allow nginx worker group to read the password hashes without exposing them.
chown root:nginx /etc/nginx/.voice-studio-htpasswd
chmod 0640 /etc/nginx/.voice-studio-htpasswd

if [ -n "${STUDIO_BACKEND_URL:-}" ] && [ -n "${STUDIO_BACKEND_HOST:-}" ] && [ -n "${STUDIO_BACKEND_GATEWAY_TOKEN:-}" ]; then
    # Substitute exactly these three variables, preserving native nginx variables.
    envsubst '${STUDIO_BACKEND_URL} ${STUDIO_BACKEND_HOST} ${STUDIO_BACKEND_GATEWAY_TOKEN}' \
        < /etc/nginx/nginx.backend.conf.template > /etc/nginx/conf.d/default.conf
    echo "Voice Studio backend proxy is configured"
else
    echo "Voice Studio running frontend-only preview; backend routes disabled"
fi
exec nginx -g "daemon off;"
