#!/usr/bin/env python3
"""
stream_ui.py

A single Streamlit UI that provides:
- Sidebar for DB & OAuth config, retrieval method, 'Save Configuration'.
- Main page for:
  - "Fetch Emails" button (retrieves & stores emails).
  - A dynamic "Rule Editor" 
    * Add/Remove conditions
    * Add/Remove actions (including new actions: Star, Unstar, Archive, Trash)
    * Match policy (All/Any)
    * Load existing rules from JSON
    * Apply rules (saves JSON + calls rule_processor to act on emails).
"""
import os
import json
import streamlit as st

import settings
from postgres_client import init_database_if_missing, init_pg_table
from rules_actions import apply_email_rules, fetch_and_save_emails

# ---------------------------------------------
# Constants: Fields, Operators, Actions, etc.
# ---------------------------------------------
FIELDS = ["From", "To", "Subject", "Received Date/Time", "Message"]
TEXT_OPERATORS = ["contains", "does not contain", "equals", "does not equal"]
DATE_OPERATORS = ["less than", "greater than"]

# We add more Gmail-like actions here
ACTIONS = [
    "Mark as Read", 
    "Mark as Unread", 
    "Move Message",
    "Star",
    "Unstar",
    "Archive",
    "Trash"
]
MOVE_DESTINATIONS = ["Inbox", "Forum", "Updates", "Promotions"]

# ----------------------------
# Session State Initialization
# ----------------------------
if "conditions" not in st.session_state:
    st.session_state["conditions"] = []
if "actions" not in st.session_state:
    st.session_state["actions"] = []
if "match_policy" not in st.session_state:
    st.session_state["match_policy"] = "All"

# ---------------------------------------
# Helper Functions for Rule Editor Logic
# ---------------------------------------
def load_rules_from_file():
    """Load existing rules from the JSON file, if it exists."""
    path = settings.EMAIL_RULES_FILE
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_rules_to_file(ruleset):
    """Save the given ruleset to the JSON file."""
    path = settings.EMAIL_RULES_FILE
    with open(path, "w") as f:
        json.dump(ruleset, f, indent=4)

def reset_editor_from_file():
    """Load the existing JSON file and populate session_state with its conditions/actions."""
    data = load_rules_from_file()
    if not data:
        st.session_state["conditions"] = []
        st.session_state["actions"] = []
        st.session_state["match_policy"] = "All"
        return
    st.session_state["match_policy"] = data.get("match_policy", "All")
    
    # Convert each condition
    st.session_state["conditions"] = []
    for c in data.get("rules", []):
        st.session_state["conditions"].append({
            "field": c.get("field", "From"),
            "predicate": c.get("predicate", "contains"),
            "value": c.get("value", ""),
            "unit": c.get("unit", "days")
        })
    # Convert each action
    st.session_state["actions"] = []
    for a in data.get("actions", []):
        act = {"action": a.get("action", "mark as read")}
        # If move message, store destination
        if act["action"] == "move message":
            act["destination"] = a.get("destination", "inbox")
        st.session_state["actions"].append(act)

def build_ruleset():
    """Build the final ruleset dict from session_state conditions/actions."""
    # Convert conditions
    rules = []
    for c in st.session_state["conditions"]:
        rule_dict = {
            "field": c["field"],
            "predicate": c["predicate"],
            "value": c["value"]
        }
        if c["field"] == "Received Date/Time":
            rule_dict["unit"] = c["unit"]
        rules.append(rule_dict)
    # Convert actions
    actions = []
    for a in st.session_state["actions"]:
        act_dict = {"action": a["action"]}
        if a["action"] == "move message":
            act_dict["destination"] = a.get("destination", "inbox")
        actions.append(act_dict)
    return {
        "match_policy": st.session_state["match_policy"],
        "rules": rules,
        "actions": actions
    }

# -----------------------
# Sidebar Configuration
# -----------------------
st.sidebar.title("Configuration")

# Database inputs
username = st.sidebar.text_input("PostgreSQL Username", value="postgres")
password = st.sidebar.text_input("PostgreSQL Password", type="password")
dbname = st.sidebar.text_input("Database Name",)
tablename = st.sidebar.text_input("Table Name", value="emails")

# OAuth credentials uploader
uploaded_oauth = st.sidebar.file_uploader("Upload OAuth Credentials (JSON)", type=["json"])

# Retrieval Method
retrieval_method = st.sidebar.selectbox("Retrieval Method", ["Timeframe","Number of Messages"])
if retrieval_method == "Number of Messages":
    message_count = st.sidebar.text_input("Number of Messages", value="10")
else:
    timeframe_value = st.sidebar.text_input("Timeframe Value", value="7")
    timeframe_unit = st.sidebar.selectbox("Timeframe Unit", ["Days", "Months"])

# Button: Save Configuration
if st.sidebar.button("Save Configuration"):
    # 1) Update DB config
    settings.DATABASE_SETTINGS.clear()
    settings.DATABASE_SETTINGS.update({
        "host": "localhost",
        "user": username.strip(),
        "password": password,
        "database": dbname.strip(),
        "table": tablename.strip()
    })

    # 2) Handle OAuth file upload
    if uploaded_oauth is None:
        st.sidebar.error("No OAuth credentials file uploaded.")
    else:
        with open("temp_oauth_creds.json", "wb") as f:
            f.write(uploaded_oauth.getvalue())
        settings.OAUTH_FILE = "temp_oauth_creds.json"
        st.sidebar.success("OAuth file saved as 'temp_oauth_creds.json'.")

        # 3) Initialize DB & table
        db_result = init_database_if_missing(settings.DATABASE_SETTINGS)
        table_result = init_pg_table()
        st.sidebar.write(db_result)
        st.sidebar.write(table_result)

# --------------------------
# Main Page: Fetch & Editor
# --------------------------
st.title("Rule-based email processing")

# Fetch Emails
st.subheader("Fetch Emails")
if st.button("Fetch Emails"):
    if retrieval_method == "Number of Messages":
        msg_param = message_count.strip() or "10"
    else:
        num = timeframe_value.strip() or "7"
        unit = timeframe_unit.lower()
        letter = "d" if unit == "days" else "m"
        msg_param = f"newer_than:{num}{letter}"

    fetch_result = fetch_and_save_emails(msg_param)
    st.write("**Fetch Emails Result:**")
    st.text(fetch_result)

# -------------------
# Rule Editor Section
# -------------------
st.header("Rule Editor")

# Load existing rules button
if st.button("Load Existing Rules"):
    reset_editor_from_file()
    st.success("Loaded existing rules from file (if any).")

# Match Policy
st.session_state["match_policy"] = st.radio("Match Policy (All/Any):",
    ["All", "Any"],
    index=0 if st.session_state["match_policy"] == "All" else 1
)

st.subheader("Conditions")
st.write("Add one or more conditions. Each row is [Field, Predicate, Value, Unit (if date-based)].")

for i, cond in enumerate(st.session_state["conditions"]):
    c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 1.5, 1.5, 0.7])
    # Field
    cond["field"] = c1.selectbox("Field", FIELDS,
                                 index=FIELDS.index(cond["field"]) if cond["field"] in FIELDS else 0,
                                 key=f"field_{i}")
    # Predicate
    possible_preds = DATE_OPERATORS if cond["field"] == "Received Date/Time" else TEXT_OPERATORS
    if cond["predicate"] not in possible_preds:
        cond["predicate"] = possible_preds[0]
    cond["predicate"] = c2.selectbox("Predicate", possible_preds,
                                     index=possible_preds.index(cond["predicate"]) if cond["predicate"] in possible_preds else 0,
                                     key=f"pred_{i}")
    # Value
    cond["value"] = c3.text_input("Value", cond["value"], key=f"value_{i}")

    # If date-based, show unit
    if cond["field"] == "Received Date/Time":
        cond["unit"] = c4.selectbox("Unit", ["days", "months"],
                                    index=0 if cond["unit"] == "days" else 1,
                                    key=f"unit_{i}")
    else:
        c4.write("-")

    # Add some spacing so the button aligns better
    c5.markdown("<br>", unsafe_allow_html=True)
    if c5.button("❌", key=f"remove_cond_{i}"):
        st.session_state["conditions"].pop(i)
        # If your Streamlit version supports it:
        st.rerun()

if st.button("Add Condition"):
    st.session_state["conditions"].append({
        "field": "From",
        "predicate": "contains",
        "value": "",
        "unit": "days"
    })
    # If your Streamlit version supports it:
    st.rerun()

st.subheader("Actions")
st.write("Add one or more actions. For 'Move Message', pick a destination. (Now includes Star, Unstar, Archive, Trash)")

for j, act in enumerate(st.session_state["actions"]):
    a1, a2, a3 = st.columns([2, 2, 0.7])
    # Action
    if act["action"].lower() not in [
        "mark as read", 
        "mark as unread", 
        "move message",
        "star",
        "unstar",
        "archive",
        "trash"
    ]:
        act["action"] = "mark as read"
    # Figure out the current index
    action_lower = act["action"].lower()
    action_map = {
        "mark as read": 0,
        "mark as unread": 1,
        "move message": 2,
        "star": 3,
        "unstar": 4,
        "archive": 5,
        "trash": 6
    }
    current_index = action_map[action_lower]

    chosen_action = a1.selectbox("Action", ACTIONS, index=current_index, key=f"act_{j}")
    act["action"] = chosen_action.lower()

    if act["action"] == "move message":
        if "destination" not in act:
            act["destination"] = "Inbox"
        # find index
        dest_index = 0
        for idx, d in enumerate(MOVE_DESTINATIONS):
            if d.lower() == act["destination"].lower():
                dest_index = idx
                break
        chosen_dest = a2.selectbox("Destination", MOVE_DESTINATIONS, index=dest_index, key=f"dest_{j}")
        act["destination"] = chosen_dest.lower()
    else:
        a2.write("-")

    a3.markdown("<br>", unsafe_allow_html=True)
    if a3.button("❌", key=f"remove_act_{j}"):
        st.session_state["actions"].pop(j)
        # If your Streamlit version supports it:
        st.rerun()

if st.button("Add Action"):
    st.session_state["actions"].append({"action": "mark as read"})
    # If your Streamlit version supports it:
    st.rerun()

# -----------------------------------
# Apply Rules: Save + Execute Actions
# -----------------------------------
st.subheader("Apply Rules")
if st.button("Apply Rules Now"):
    final_ruleset = build_ruleset()
    save_rules_to_file(final_ruleset)
    from rules_actions import apply_email_rules
    result = apply_email_rules()
    st.success("Rules saved and applied!")
    st.write("**Final Ruleset:**")
    st.json(final_ruleset)
    st.write("**Rule Processor Output:**")
    st.text(result)
