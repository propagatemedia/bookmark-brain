"""PyInstaller runtime hook: provide HTTPS roots for portable python.org builds."""
import os
import certifi

# Keep an explicitly configured enterprise trust bundle if supplied by the user.
os.environ.setdefault('SSL_CERT_FILE', certifi.where())
