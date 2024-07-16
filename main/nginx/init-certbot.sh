#!/bin/bash
# Start Nginx in the background
nginx &
# Wait for Nginx to start
sleep 5
# Run Certbot to obtain SSL certificates
certbot certonly --nginx -d automatedtrading.systems 
--non-interactive 
--agree-tos -m deximasof@google.com
# Restart Nginx to apply the new 
# certificates
nginx -s reload
# Keep the container running
tail -f /var/log/nginx/access.log 
/var/log/nginx/error.log

