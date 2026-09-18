#!/usr/bin/env python3
"""
Jira Integration for Finance Tracker
Connect Finance Tracker to Jira for issue tracking & automation
"""

import requests
import json
import os
from datetime import datetime
from typing import Optional, Dict, List
from base64 import b64encode

class JiraClient:
    def __init__(self, domain: str, email: str, api_token: str, project_key: str):
        """
        Initialize Jira client
        domain: Jira cloud domain (contoh: company.atlassian.net)
        email: Email yang terdaftar di Jira
        api_token: API token dari Jira (generate di settings)
        project_key: Project key (contoh: FIN, TRACK)
        """
        self.domain = domain
        self.email = email
        self.api_token = api_token
        self.project_key = project_key
        self.base_url = f"https://{domain}/rest/api/3"
        
        # Setup auth header
        auth_string = f"{email}:{api_token}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = b64encode(auth_bytes).decode('utf-8')
        
        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> bool:
        """Test Jira connection"""
        try:
            response = requests.get(
                f"{self.base_url}/myself",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                user = response.json()
                print(f"✅ Connected to Jira")
                print(f"   User: {user.get('displayName')} ({user.get('emailAddress')})")
                return True
            else:
                print(f"❌ Connection failed: {response.status_code}")
                print(f"   {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def create_issue(self, summary: str, description: str, issue_type: str = "Task", 
                    priority: str = "Medium", labels: List[str] = None) -> Optional[Dict]:
        """Create new Jira issue"""
        try:
            payload = {
                "fields": {
                    "project": {"key": self.project_key},
                    "summary": summary,
                    "description": {
                        "version": 1,
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": description
                                    }
                                ]
                            }
                        ]
                    },
                    "issuetype": {"name": issue_type},
                    "priority": {"name": priority}
                }
            }
            
            if labels:
                payload["fields"]["labels"] = labels
            
            response = requests.post(
                f"{self.base_url}/issues",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                issue = response.json()
                print(f"✅ Issue created: {issue['key']}")
                return issue
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_issue(self, issue_key: str) -> Optional[Dict]:
        """Get issue details"""
        try:
            response = requests.get(
                f"{self.base_url}/issues/{issue_key}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Issue not found: {issue_key}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def search_issues(self, jql: str, max_results: int = 10) -> Optional[List[Dict]]:
        """Search issues using JQL"""
        try:
            params = {
                "jql": jql,
                "maxResults": max_results
            }
            
            response = requests.get(
                f"{self.base_url}/search",
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('issues', [])
            else:
                print(f"❌ Search failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def update_issue(self, issue_key: str, updates: Dict) -> bool:
        """Update issue fields"""
        try:
            payload = {"fields": updates}
            
            response = requests.put(
                f"{self.base_url}/issues/{issue_key}",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                print(f"✅ Issue updated: {issue_key}")
                return True
            else:
                print(f"❌ Update failed: {response.status_code}")
                print(f"   {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def add_comment(self, issue_key: str, comment_text: str) -> bool:
        """Add comment to issue"""
        try:
            payload = {
                "body": {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": comment_text
                                }
                            ]
                        }
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/issues/{issue_key}/comments",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Comment added to {issue_key}")
                return True
            else:
                print(f"❌ Failed to add comment: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def transition_issue(self, issue_key: str, transition_name: str) -> bool:
        """Transition issue to different status"""
        try:
            # Get available transitions
            response = requests.get(
                f"{self.base_url}/issues/{issue_key}/transitions",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to get transitions: {response.status_code}")
                return False
            
            transitions = response.json().get('transitions', [])
            
            # Find matching transition
            transition_id = None
            for trans in transitions:
                if trans.get('name').lower() == transition_name.lower():
                    transition_id = trans.get('id')
                    break
            
            if not transition_id:
                print(f"❌ Transition '{transition_name}' not found")
                print(f"   Available: {[t.get('name') for t in transitions]}")
                return False
            
            # Execute transition
            payload = {"transition": {"id": transition_id}}
            
            response = requests.post(
                f"{self.base_url}/issues/{issue_key}/transitions",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                print(f"✅ Issue transitioned: {issue_key} → {transition_name}")
                return True
            else:
                print(f"❌ Transition failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def get_projects(self) -> Optional[List[Dict]]:
        """Get all accessible projects"""
        try:
            response = requests.get(
                f"{self.base_url}/projects",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get projects: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

# CLI Interface
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 jira_client.py <command> [args]")
        print("\nCommands:")
        print("  test <domain> <email> <api_token> <project_key>")
        print("  create <domain> <email> <api_token> <project_key> <summary> <description>")
        print("  search <domain> <email> <api_token> <project_key> <jql>")
        print("  comment <domain> <email> <api_token> <issue_key> <comment_text>")
        print("\nExample:")
        print("  python3 jira_client.py test mycompany.atlassian.net user@email.com token123 FIN")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'test':
        if len(sys.argv) < 6:
            print("Usage: python3 jira_client.py test <domain> <email> <api_token> <project_key>")
            sys.exit(1)
        
        domain = sys.argv[2]
        email = sys.argv[3]
        api_token = sys.argv[4]
        project_key = sys.argv[5]
        
        client = JiraClient(domain, email, api_token, project_key)
        client.test_connection()
    
    elif command == 'create':
        if len(sys.argv) < 8:
            print("Usage: python3 jira_client.py create <domain> <email> <api_token> <project_key> <summary> <description>")
            sys.exit(1)
        
        domain = sys.argv[2]
        email = sys.argv[3]
        api_token = sys.argv[4]
        project_key = sys.argv[5]
        summary = sys.argv[6]
        description = sys.argv[7]
        
        client = JiraClient(domain, email, api_token, project_key)
        client.create_issue(summary, description, labels=["finance-tracker"])
    
    elif command == 'search':
        if len(sys.argv) < 7:
            print("Usage: python3 jira_client.py search <domain> <email> <api_token> <project_key> <jql>")
            sys.exit(1)
        
        domain = sys.argv[2]
        email = sys.argv[3]
        api_token = sys.argv[4]
        project_key = sys.argv[5]
        jql = sys.argv[6]
        
        client = JiraClient(domain, email, api_token, project_key)
        issues = client.search_issues(jql)
        if issues:
            print(f"\n✅ Found {len(issues)} issues:")
            for issue in issues:
                print(f"  • {issue['key']}: {issue['fields']['summary']}")
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)
