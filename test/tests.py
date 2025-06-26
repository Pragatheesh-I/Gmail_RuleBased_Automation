#!/usr/bin/env python3

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys, os

# Append the parent directory so our modules can be imported.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import functions from our updated project modules
import mail_logic
import rules_actions

# ----------------------- Unit Tests for Mail Logic -----------------------
class TestMailService(unittest.TestCase):
    def test_convert_date_string_valid(self):
        # Test with a proper email date header.
        date_str = "Tue, 15 Nov 2022 12:45:26 +0000"
        dt = mail_logic.convert_date_string(date_str)
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.strftime('%Y-%m-%d'), '2022-11-15')
    
    def test_convert_date_string_invalid(self):
        # When the date string is invalid, expect None.
        date_str = "Invalid Date String"
        dt = mail_logic.convert_date_string(date_str)
        self.assertIsNone(dt)

# ----------------------- Unit Tests for Rules & Actions -----------------------
class TestRuleProcessorUnit(unittest.TestCase):
    def test_check_condition_contains(self):
        # Check if the 'contains' condition works for text.
        condition = {"predicate": "contains", "value": "test"}
        self.assertTrue(rules_actions.check_condition("This is a test email", condition))
        self.assertFalse(rules_actions.check_condition("No match here", condition))
    
    def test_check_condition_date_less_than(self):
        # Test the date condition: email received less than 7 days ago.
        condition = {"predicate": "less than", "value": "7", "unit": "days"}
        email_date = datetime.now() - timedelta(days=5)
        self.assertTrue(rules_actions.check_condition(email_date, condition))
    
    def test_check_condition_date_greater_than(self):
        # Test the date condition: email received more than 7 days ago.
        condition = {"predicate": "greater than", "value": "7", "unit": "days"}
        email_date = datetime.now() - timedelta(days=10)
        self.assertTrue(rules_actions.check_condition(email_date, condition))
    
    def test_evaluate_email_rules_all(self):
        # Test evaluating an email when ALL conditions must match.
        email = {
            "sender": "example@example.com",  # ✅ updated from 'from'
            "subject": "Test Email",
            "received_date": datetime.now() - timedelta(days=3),
            "message": "This is a test email."
        }

        ruleset = {
            "match_policy": "All",
            "rules": [
                {"field": "From", "predicate": "contains", "value": "example"},
                {"field": "Subject", "predicate": "contains", "value": "Test"}
            ]
        }
        self.assertTrue(rules_actions.evaluate_email_rules(email, ruleset))
    
    def test_evaluate_email_rules_any(self):
        # Test evaluating an email when ANY condition is enough to match.
        email = {
            "sender": "example@example.com",  # ✅ updated from 'from'
            "subject": "Test Email",
            "received_date": datetime.now() - timedelta(days=3),
            "message": "This is a test email."
        }
        ruleset = {
            "match_policy": "Any",
            "rules": [
                {"field": "From", "predicate": "contains", "value": "example"},
                {"field": "Subject", "predicate": "contains", "value": "Email"}
            ]
        }
        # Since the subject contains "Email", at least one condition is met.
        self.assertTrue(rules_actions.evaluate_email_rules(email, ruleset))

# ----------------------- Integration Tests -----------------------
class TestIntegration(unittest.TestCase):
    @patch('rules_actions.insert_email_pg')
    @patch('mail_logic.retrieve_email')
    @patch('mail_logic.fetch_emails')
    @patch('mail_logic.authenticate_email_service')
    def test_fetch_and_save_emails_integration(self, mock_auth, mock_fetch, mock_retrieve, mock_insert):
        mock_auth.return_value = MagicMock()
        mock_fetch.return_value = [{"id": "12345"}]
        mock_retrieve.return_value = {
            "email_id": "12345",
            "sender": "test@example.com",
            "recipient": "you@example.com",
            "subject": "Test Email",
            "received_date": datetime.now(),
            "message": "Testing"
        }
        mock_insert.return_value = "Stored email 12345"

        from rules_actions import fetch_and_save_emails
        result = fetch_and_save_emails("1")
        self.assertIn("Stored email 12345", result)


    @patch('rules_actions.check_condition')
    @patch('rules_actions.get_emails_pg')
    @patch('rules_actions.execute_email_actions')
    def test_apply_email_rules_integration(self, mock_execute_actions, mock_get_emails, mock_authorize):
        # Setup mocks to simulate the rules processing flow.
        fake_service = MagicMock()
        mock_authorize.return_value = fake_service
        
        # Simulate fetching one fake email from the database.
        fake_email = {
            "email_id": "67890",
            "from": "rule@example.com",
            "subject": "Rule Test",
            "received_date": datetime.now() - timedelta(days=2),
            "message": "Apply rule."
        }
        mock_get_emails.return_value = [fake_email]
        
        # Create a fake ruleset.
        fake_ruleset = {
            "match_policy": "All",
            "rules": [
                {"field": "From", "predicate": "contains", "value": "rule"}
            ],
            "actions": [{"action": "mark as read"}]
        }
        
        # Patch load_email_rules to return our fake ruleset.
        with patch('rules_actions.load_email_rules', return_value=fake_ruleset):
            # Simulate execute_email_actions returning a success message.
            mock_execute_actions.return_value = "Email 67890 marked as read."
            result = rules_actions.apply_email_rules()
            self.assertIn("Email 67890", result)
            self.assertIn("marked as read", result)

if __name__ == "__main__":
    unittest.main()
