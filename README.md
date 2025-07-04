# 📬 Gmail Rule Automation System

A full-stack backend project to automate Gmail inbox management using user-defined rules. Built with **Python**, **Gmail API**, **PostgreSQL**, and **Streamlit UI**.

---

## 🚀 Features

- ✅ OAuth 2.0 Authentication with Gmail
- 📥 Fetch emails using count or time-based filters
- 🧠 Define custom rules visually (e.g., “If subject contains ‘Amazon’, move to Promotions”)
- 🏷️ Supports Gmail actions: Mark as Read/Unread, Move, Star, Archive, Trash
- 🗃️ Emails are stored in PostgreSQL for persistent rule processing
- 🧪 Includes unit + integration tests (mock-based for safe execution)

---

## 📸 UI Preview

<img src="assets/ui.png" />  
<br><br>
<img src="assets/ui2.png"/>



---

## 🧱 Project Structure

```
📁 gmail_filter_project/
├── mail_logic.py           # Gmail API OAuth & email retrieval
├── postgres_client.py      # PostgreSQL interaction logic
├── rules_actions.py        # Rule evaluation & Gmail action executor
├── stream_ui.py            # Streamlit frontend
├── settings.py             # Global config (OAuth file, DB settings)
├── test/
│   └── tests.py            # Unit + integration test suite
├── email_rules.json        # Stores user's rule config (generated via UI)
└── requirements.txt        # Python dependencies
```



---

## 🛠️ Setup Instructions

### 1. Clone the Repo

```
git clone https://github.com/Pragatheesh-I/Gmail_RuleBased_Automation.git
cd Gmail_RuleBased_Automation
```

### 2. Install Dependencies

```
pip install -r requirements.txt
```

### 3. Set Up Google OAuth

- Go to Google Cloud Console
- Create a new project → Enable Gmail API
- Create OAuth client credentials (Desktop App)
- Download credentials.json and rename to oauth_creds.json
- Upload this file via the Streamlit UI

### 4. Run the App

```
streamlit run stream_ui.py
```
---

### ✅ Running Tests

```
python test\\tests.py
```

Tests include:
- Date parsing and validation
- Rule evaluation logic
- Mocked Gmail API interactions
- Mocked DB inserts and fetches

---

### ✏️ Rule Editor Details

Conditions

- Field: From, To, Subject, Received Date/Time, Message
- Predicate (for text): contains, does not contain, equals, does not equal
- Predicate (for date): less than, greater than (with "days" or "months")
- Value: The text or number for comparison

Actions

- Mark as Read/Unread
- Move Message (Inbox, Forum, Updates, Promotions)
- Star/Unstar
- Archive (remove INBOX label)
- Trash (moves email to Trash)

---

### 💡 Future Improvements

- Add user authentication to the frontend
- Add frontend dashboard for analytics
- Dockerize the backend
- Add scheduling with CRON or Celery

---

### 👨‍💻 Author
Pragatheesh — Engineering Student passionate about clean backend systems and automation.

---

### 📌 License

📝 This project is open-source and available under the MIT License.
