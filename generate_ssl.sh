#!/bin/bash

# Create SSL directory if it doesn't exist
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem \
    -subj "/C=KR/ST=Seoul/L=Seoul/O=ParaGourmet/OU=IT/CN=141.147.147.76"

echo "✅ Self-signed SSL certificate generated"
echo "⚠️  Browser will show security warning for self-signed certificates"
echo "💡 For production, use Let's Encrypt or a proper CA certificate"