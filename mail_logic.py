#!/usr/bin/env python3
"""
mail_logic.py
Handles:
- Gmail OAuth authentication
- Listing and retrieving emails via the Gmail API
"""

import os
import pickle
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import settings

def authenticate_email_service():
    """
    Log in to Gmail using OAuth and return a Gmail service object.
    """
    creds = None
    token_storage = "service_token.pickle"
    
    # Load saved credentials if available
    if os.path.exists(token_storage):
        with open(token_storage, "rb") as token:
            creds = pickle.load(token)
    
    # If credentials are missing/invalid, refresh or prompt login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(settings.OAUTH_FILE):
                raise FileNotFoundError(
                    f"Missing {settings.OAUTH_FILE}. Please provide your OAuth credentials file."
                )
            flow = InstalledAppFlow.from_client_secrets_file(settings.OAUTH_FILE, settings.PERMISSIONS)
            creds = flow.run_local_server(port=0)
        # Save for next time
        with open(token_storage, "wb") as token:
            pickle.dump(creds, token)
    
    return build("gmail", "v1", credentials=creds)

def fetch_emails(service, count_or_query="50"):
    """
    Fetch a set of emails from Gmail. If count_or_query is a digit (like "50"),
    get that many. Otherwise, treat it as a Gmail search query (e.g., "newer_than:7d").
    """
    emails = []
    
    if count_or_query.isdigit():
        desired_count = int(count_or_query)
        query_text = ""
        max_results = min(desired_count, 100)
    else:
        query_text = count_or_query
        max_results = 100

    response = service.users().messages().list(
        userId="me", maxResults=max_results, q=query_text
    ).execute()
    emails.extend(response.get("messages", []))
    
    # Keep fetching pages if needed
    while "nextPageToken" in response and (not count_or_query.isdigit() or len(emails) < desired_count):
        next_token = response["nextPageToken"]
        response = service.users().messages().list(
            userId="me", maxResults=max_results, q=query_text, pageToken=next_token
        ).execute()
        emails.extend(response.get("messages", []))
    
    if count_or_query.isdigit():
        emails = emails[:desired_count]
    
    return emails

def retrieve_email(service, msg_id):
    """
    Retrieve details for a single email by ID. Returns a dict with keys:
      email_id, sender, recipient, subject, received_date, message
    """
    message = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()
    headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}

    email_data = {
        "email_id": msg_id,
        "sender": headers.get("from", ""),
        "recipient": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "received_date": convert_date_string(headers.get("date", "")),
        "message": message.get("snippet", "")
    }
    return email_data

def convert_date_string(date_str):
    """
    Convert an email's date header into a datetime object. Returns None if parsing fails.
    """
    try:
        return datetime.strptime(date_str[:31], '%a, %d %b %Y %H:%M:%S %z')
    except Exception:
        return None
