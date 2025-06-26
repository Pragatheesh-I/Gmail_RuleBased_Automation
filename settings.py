"""
settings.py
- Contains the global settings
"""
import os

PERMISSIONS = ['https://www.googleapis.com/auth/gmail.modify']

# Populated at runtime with database credentials + table name
DATABASE_SETTINGS = {}

# Path to OAuth credentials JSON
OAUTH_FILE = "oauth_creds.json"

# File containing JSON rules for processing emails
EMAIL_RULES_FILE = "email_rules.json"

def get_env_variable(name, default=None):
    """
    Fetch environment variable or return default value.
    Useful for future scalability (e.g., Docker deployment).
    """
    return os.environ.get(name, default)