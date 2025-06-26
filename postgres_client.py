#!/usr/bin/env python3
"""
postgres_client.py
Handles:
- Database creation (if missing)
- Table creation using a user-specified table name
- Insert email records
- Retrieve stored emails
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import settings

def init_database_if_missing(connection_params):
    """
    Create the target database if it doesn't exist, using the 'postgres' default DB.
    """
    target_database = connection_params.get("database")
    try:
        conn = psycopg2.connect(
            host=connection_params.get("host"),
            user=connection_params.get("user"),
            password=connection_params.get("password"),
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        # Check if the database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_database,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(f"CREATE DATABASE {target_database};")
            result = f"Database '{target_database}' created successfully."
        else:
            result = f"Database '{target_database}' already exists."
        cur.close()
        conn.close()
        return result
    except Exception as e:
        return f"Error initializing database: {e}"

def init_pg_table():
    """
    Create the user-specified table if it doesn't exist.
    """
    try:
        connection_params = settings.DATABASE_SETTINGS
        table_name = connection_params.get("table", "emails")

        conn = psycopg2.connect(
            host=connection_params.get("host"),
            user=connection_params.get("user"),
            password=connection_params.get("password"),
            dbname=connection_params.get("database")
        )
        cur = conn.cursor()
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            email_id VARCHAR(255) UNIQUE,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            received_date TIMESTAMPTZ,
            message TEXT
        );
        """
        cur.execute(create_table_sql)
        conn.commit()
        cur.close()
        conn.close()
        return f"Table '{table_name}' created or already exists."
    except Exception as e:
        return f"Error creating table: {e}"

def insert_email_pg(email_info):
    """
    Insert a single email record into the user-specified table.
    """
    try:
        connection_params = settings.DATABASE_SETTINGS
        table_name = connection_params.get("table", "emails")

        conn = psycopg2.connect(
            host=connection_params.get("host"),
            user=connection_params.get("user"),
            password=connection_params.get("password"),
            dbname=connection_params.get("database")
        )
        cur = conn.cursor()
        insert_sql = f"""
        INSERT INTO {table_name} (email_id, sender, recipient, subject, received_date, message)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (email_id) DO NOTHING;
        """
        cur.execute(insert_sql, (
            email_info.get("email_id"),
            email_info.get("sender"),
            email_info.get("recipient"),
            email_info.get("subject"),
            email_info.get("received_date"),
            email_info.get("message")
        ))
        conn.commit()
        cur.close()
        conn.close()
        return f"Email {email_info.get('email_id')} inserted."
    except Exception as e:
        return f"Error inserting email: {e}"

def get_emails_pg():
    """
    Retrieve all emails from the user-specified table.
    """
    try:
        connection_params = settings.DATABASE_SETTINGS
        table_name = connection_params.get("table", "emails")

        conn = psycopg2.connect(
            host=connection_params.get("host"),
            user=connection_params.get("user"),
            password=connection_params.get("password"),
            dbname=connection_params.get("database")
        )
        cur = conn.cursor()
        select_sql = f"""
        SELECT email_id, sender, recipient, subject, received_date, message
        FROM {table_name};
        """
        cur.execute(select_sql)
        rows = cur.fetchall()
        emails_list = []
        for row in rows:
            email_rec = {
                "email_id": row[0],
                "sender": row[1],
                "recipient": row[2],
                "subject": row[3],
                "received_date": row[4],
                "message": row[5]
            }
            emails_list.append(email_rec)
        cur.close()
        conn.close()
        return emails_list
    except Exception as e:
        return f"Error retrieving emails: {e}"
