#!/usr/bin/env python3
"""
rules_actions.py
Handles:
- Loading rules from JSON
- Checking each email against those rules
- Executing actions (mark as read/unread, move)
- Fetching emails from Gmail (by count/query) and saving to the DB
"""
import os
import json
from datetime import datetime
from mail_logic import authenticate_email_service
from postgres_client import get_emails_pg, insert_email_pg
from settings import EMAIL_RULES_FILE

# Mapping from folder names to Gmail label IDs
LABELS_MAP = {
    "inbox": "INBOX",
    "forum": "CATEGORY_FORUMS",
    "updates": "CATEGORY_UPDATES",
    "promotions": "CATEGORY_PROMOTIONS"
}

def load_email_rules():
    """
    Load the rules from a JSON file.
    Returns the rules dict or None on error.
    """
    if not os.path.exists(EMAIL_RULES_FILE):
        print("Rules file not found. Please create one using the Rule Editor.")
        return None
    with open(EMAIL_RULES_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            print("Error decoding the rules file. Check its contents.")
            return None

def check_condition(email_value, condition):
    """
    Evaluate a single condition on an email field.
    For date fields, supports 'less than' or 'greater than'.
    For text fields, supports 'contains', 'does not contain', 'equals', 'does not equal'.
    """
    operator = condition["predicate"].lower()
    cond_value = condition["value"]
    
    # Date-based checks
    if isinstance(email_value, datetime) and operator in ["less than", "greater than"]:
        try:
            threshold = int(cond_value)
        except ValueError:
            return False
        unit = condition.get("unit", "days").lower()
        if unit == "months":
            threshold *= 30  # approximate
        elapsed_days = (datetime.now(email_value.tzinfo) - email_value).days
        if operator == "less than":
            return elapsed_days < threshold
        elif operator == "greater than":
            return elapsed_days > threshold
    
    # Text-based checks
    elif isinstance(email_value, str):
        if operator == "contains":
            return cond_value.lower() in email_value.lower()
        elif operator == "does not contain":
            return cond_value.lower() not in email_value.lower()
        elif operator == "equals":
            return email_value.lower() == cond_value.lower()
        elif operator == "does not equal":
            return email_value.lower() != cond_value.lower()
    
    return False

def evaluate_email_rules(email, ruleset):
    """
    Check an email against the given ruleset. Return True if it matches
    based on the 'match_policy' ('All' or 'Any').
    """
    evaluations = []
    for rule in ruleset.get("rules", []):
        field = rule.get("field", "").lower()
        
        # Map "From"/"To" to the correct keys in the email dict
        if field == "from":
            email_field_value = email.get("sender", "")
        elif field == "to":
            email_field_value = email.get("recipient", "")
        elif field == "subject":
            email_field_value = email.get("subject", "")
        elif "received" in field:
            email_field_value = email.get("received_date", None)
        elif field == "message":
            email_field_value = email.get("message", "")
        else:
            # fallback
            email_field_value = email.get(field, "")
        
        evaluations.append(check_condition(email_field_value, rule))
    
    match_policy = ruleset.get("match_policy", "All").lower()
    if match_policy == "all":
        return all(evaluations)
    else:
        return any(evaluations)

# rule_processor.py

def execute_email_actions(service, email_id, actions_list):
    """
    Execute actions (mark read/unread, move message, star, unstar, archive, trash) on a matching email.
    """
    results = []
    for action in actions_list:
        action_type = action.get("action", "").lower()
        try:
            if action_type == "mark as read":
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()
                results.append(f"Email {email_id} marked as read.")
            elif action_type == "mark as unread":
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={"addLabelIds": ["UNREAD"]}
                ).execute()
                results.append(f"Email {email_id} marked as unread.")
            elif action_type == "move message":
                destination = action.get("destination", "inbox").lower()
                label_map = {
                    "inbox": "INBOX",
                    "forum": "CATEGORY_FORUMS",
                    "updates": "CATEGORY_UPDATES",
                    "promotions": "CATEGORY_PROMOTIONS"
                }
                label = label_map.get(destination, destination.upper())
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={
                        "removeLabelIds": ["INBOX"],
                        "addLabelIds": [label]
                    }
                ).execute()
                results.append(f"Email {email_id} moved to {label}.")
            elif action_type == "star":
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={"addLabelIds": ["STARRED"]}
                ).execute()
                results.append(f"Email {email_id} starred.")
            elif action_type == "unstar":
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={"removeLabelIds": ["STARRED"]}
                ).execute()
                results.append(f"Email {email_id} unstarred.")
            elif action_type == "archive":
                # Remove label 'INBOX' to archive
                service.users().messages().modify(
                    userId="me", id=email_id,
                    body={"removeLabelIds": ["INBOX"]}
                ).execute()
                results.append(f"Email {email_id} archived (removed from INBOX).")
            elif action_type == "trash":
                service.users().messages().trash(userId="me", id=email_id).execute()
                results.append(f"Email {email_id} moved to trash.")
        except Exception as e:
            results.append(f"Error processing action '{action_type}' on email {email_id}: {e}")
    return "\n".join(results)


def apply_email_rules():
    """
    Load the rules, get emails from the DB, and for each matching email,
    execute the actions via Gmail API.
    """
    ruleset = load_email_rules()
    if not ruleset:
        return "Missing or invalid rules file."
    
    emails = get_emails_pg()
    if not emails or not isinstance(emails, list):
        return "No emails to process."
    
    service = authenticate_email_service()
    summary = []
    for email in emails:
        if evaluate_email_rules(email, ruleset):
            summary.append(f"Email {email['email_id']} matches rules. Executing actions...")
            actions_result = execute_email_actions(service, email["email_id"], ruleset["actions"])
            summary.append(actions_result)
    return "\n".join(summary)

def fetch_and_save_emails(message_param="10"):
    """
    Authenticate with Gmail, fetch emails by count or query, and insert them into the DB.
    """
    from mail_logic import fetch_emails, retrieve_email
    
    try:
        service = authenticate_email_service()
    except Exception as error:
        return f"Error authenticating with Gmail: {error}"
    
    messages = fetch_emails(service, message_param)
    if not messages:
        return "No messages found."
    
    results = []
    for msg in messages:
        try:
            email_details = retrieve_email(service, msg["id"])
            insert_result = insert_email_pg(email_details)
            results.append(insert_result)
        except Exception as error:
            results.append(f"Error processing message {msg['id']}: {error}")
    return "\n".join(results)
