import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json

class IndependentContentInteractionsTester:
    def __init__(self, base_url="https://c62d4176-fc83-406e-a031-ac397638707a.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_id = None
        self.auth_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test user credentials
        self.test_user_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        self.test_user_password = "TestPassword123!"
        self.test_user_name = f"Test User {datetime.now().strftime('%H%M%S')}"
        
        print(f"🔍 Testing Independent Content Interactions API at: {self.base_url}")
        print(f"📝 Test user: {self.test_user_email}")

    def run_test(self, name, method, endpoint, expected_status, data=None, auth=False, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Add authorization header if needed
        if auth and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                self.test_results.append({"name": name, "status": "PASS", "details": f"Status: {response.status_code}"})
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results.append({"name": name, "status": "FAIL", "details": f"Expected {expected_status}, got {response.status_code}"})

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({"name": name, "status": "ERROR", "details": str(e)})
            return False, {}

    def test_user_registration(self):
        """Test user registration"""
        data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
            "name": self.test_user_name
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=data
        )
        
        if success and 'access_token' in response:
            self.auth_token = response['access_token']
            self.user_id = response['user']['id']
            print(f"✅ User registered with ID: {self.user_id}")
            print(f"✅ Auth token received: {self.auth_token[:10]}...")
            return True, response
        
        return False, response

    def test_create_session(self):
        """Test session creation"""
        success, response = self.run_test(
            "Create Session",
            "POST",
            "session",
            200,
            data={}
        )
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            print(f"Session ID: {self.session_id}")
            return True, response
        return False, response

    def test_get_voting_pair(self, use_auth=False):
        """Test getting a voting pair"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            print("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Voting Pair", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Voting Pair",
            "GET",
            "voting-pair",
            200,
            auth=auth,
            params=params
        )
        
        # Verify that the pair contains items of the same type
        if success and 'item1' in response and 'item2' in response:
            if response['item1']['content_type'] == response['item2']['content_type']:
                print(f"✅ Verified: Both items are of type '{response['item1']['content_type']}'")
                return True, response
            else:
                print(f"❌ Failed: Items have different types: '{response['item1']['content_type']}' and '{response['item2']['content_type']}'")
                self.test_results.append({"name": "Verify Same Content Type", "status": "FAIL", 
                                         "details": f"Items have different types: '{response['item1']['content_type']}' and '{response['item2']['content_type']}'"})
                return False, response
        
        return success, response

    def test_content_interaction(self, content_id, interaction_type, use_auth=True, session_id=None):
        """Test content interaction (watched, want_to_watch, not_interested)"""
        data = {
            "content_id": content_id,
            "interaction_type": interaction_type,
            "priority": 3 if interaction_type == "want_to_watch" else None
        }
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif session_id or self.session_id:
            # Use guest session
            data["session_id"] = session_id or self.session_id
            auth = False
        else:
            print("❌ No session ID or auth token available for content interaction")
            self.test_results.append({"name": f"Content Interaction ({interaction_type})", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            f"Content Interaction ({interaction_type})",
            "POST",
            "content/interact",
            200,
            data=data,
            auth=auth
        )
        
        if success and response.get('success') == True:
            print(f"✅ Content interaction '{interaction_type}' recorded successfully")
            return True, response
        
        return False, response

    def test_get_content_user_status(self, content_id, use_auth=True):
        """Test getting user's interaction status with content"""
        params = {}
        
        if use_auth and self.auth_token:
            # Use authenticated user
            auth = True
        elif self.session_id:
            # Use guest session
            params = {"session_id": self.session_id}
            auth = False
        else:
            print("❌ No session ID or auth token available")
            self.test_results.append({"name": "Get Content User Status", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Get Content User Status",
            "GET",
            f"content/{content_id}/user-status",
            200,
            auth=auth,
            params=params
        )
        
        if success:
            print(f"✅ Content status retrieved:")
            print(f"  Interactions: {response.get('interactions', [])}")
            print(f"  In watchlist: {response.get('in_watchlist', False)}")
            print(f"  Watchlist type: {response.get('watchlist_type')}")
            print(f"  Has watched: {response.get('has_watched', False)}")
            print(f"  Wants to watch: {response.get('wants_to_watch', False)}")
            print(f"  Not interested: {response.get('not_interested', False)}")
            
            return True, response
        
        return False, response

    def test_submit_vote(self, winner_id, loser_id, content_type, use_auth=False):
        """Test submitting a vote"""
        data = {
            "winner_id": winner_id,
            "loser_id": loser_id,
            "content_type": content_type
        }
        
        if not use_auth or not self.auth_token:
            # Guest session vote
            if not self.session_id:
                print("❌ No session ID available")
                self.test_results.append({"name": "Submit Vote", "status": "SKIP", "details": "No session ID available"})
                return False, {}
            data["session_id"] = self.session_id
            auth = False
        else:
            # Authenticated user vote
            auth = True
        
        success, response = self.run_test(
            "Submit Vote",
            "POST",
            "vote",
            200,
            data=data,
            auth=auth
        )
        
        # Verify vote was recorded
        if success and response.get('vote_recorded') == True:
            print(f"✅ Vote recorded. Total votes: {response.get('total_votes')}")
            return True, response
        
        return success, response

    def test_independent_content_interactions(self, use_auth=True):
        """Test independent content interactions for both tiles in a voting pair"""
        print("\n🔍 Testing Independent Content Interactions...")
        
        # Get a voting pair
        pair_success, pair = self.test_get_voting_pair(use_auth=use_auth)
        if not pair_success:
            print("❌ Failed to get voting pair for independent interaction tests")
            self.test_results.append({"name": "Independent Content Interactions", "status": "FAIL", "details": "Failed to get voting pair"})
            return False
        
        # Get the content IDs from the pair
        content_id1 = pair['item1']['id']
        content_id2 = pair['item2']['id']
        
        print(f"Testing independent interactions on content pair:")
        print(f"  Item 1: {pair['item1']['title']} (ID: {content_id1})")
        print(f"  Item 2: {pair['item2']['title']} (ID: {content_id2})")
        
        # Test different interactions for each content item
        # Mark first item as "watched"
        watched_success, _ = self.test_content_interaction(
            content_id1, 
            "watched",
            use_auth=use_auth
        )
        
        if not watched_success:
            print("❌ Failed to mark first item as watched")
            self.test_results.append({"name": "Independent Content Interactions - Watched", "status": "FAIL", "details": "Failed to mark first item as watched"})
            return False
        
        # Mark second item as "want_to_watch"
        watchlist_success, _ = self.test_content_interaction(
            content_id2, 
            "want_to_watch",
            use_auth=use_auth
        )
        
        if not watchlist_success:
            print("❌ Failed to mark second item as want to watch")
            self.test_results.append({"name": "Independent Content Interactions - Want to Watch", "status": "FAIL", "details": "Failed to mark second item as want to watch"})
            return False
        
        # Verify the status of both items
        status1_success, status1 = self.test_get_content_user_status(
            content_id1, 
            use_auth=use_auth
        )
        
        status2_success, status2 = self.test_get_content_user_status(
            content_id2, 
            use_auth=use_auth
        )
        
        if not status1_success or not status2_success:
            print("❌ Failed to get content status")
            self.test_results.append({"name": "Independent Content Interactions - Status Check", "status": "FAIL", "details": "Failed to get content status"})
            return False
        
        # Verify that the interactions are independent
        if status1.get('has_watched', False) and status2.get('wants_to_watch', False):
            print("✅ Verified independent interactions:")
            print(f"  Item 1 ({pair['item1']['title']}): Marked as watched")
            print(f"  Item 2 ({pair['item2']['title']}): Added to watchlist")
            self.test_results.append({"name": "Independent Content Interactions", "status": "PASS", "details": "Successfully verified independent interactions for both items"})
            
            # Now test changing an interaction
            print("\nTesting interaction change...")
            
            # Change first item from "watched" to "not_interested"
            change_success, _ = self.test_content_interaction(
                content_id1, 
                "not_interested",
                use_auth=use_auth
            )
            
            if not change_success:
                print("❌ Failed to change interaction")
                self.test_results.append({"name": "Independent Content Interactions - Change", "status": "FAIL", "details": "Failed to change interaction"})
                return False
            
            # Verify the change
            status1_after_success, status1_after = self.test_get_content_user_status(
                content_id1, 
                use_auth=use_auth
            )
            
            # Verify second item status hasn't changed
            status2_after_success, status2_after = self.test_get_content_user_status(
                content_id2, 
                use_auth=use_auth
            )
            
            if not status1_after_success or not status2_after_success:
                print("❌ Failed to get updated content status")
                self.test_results.append({"name": "Independent Content Interactions - Change Verification", "status": "FAIL", "details": "Failed to get updated content status"})
                return False
            
            if status1_after.get('not_interested', False) and status2_after.get('wants_to_watch', False):
                print("✅ Successfully changed interaction while maintaining independence:")
                print(f"  Item 1 ({pair['item1']['title']}): Changed from 'watched' to 'not interested'")
                print(f"  Item 2 ({pair['item2']['title']}): Still 'want to watch' (unchanged)")
                self.test_results.append({"name": "Independent Content Interactions - Change", "status": "PASS", "details": "Successfully changed interaction while maintaining independence"})
                
                # Test voting after interactions
                print("\nTesting voting after setting interactions...")
                vote_success, _ = self.test_submit_vote(
                    content_id1,  # Vote for the first item
                    content_id2,
                    pair['content_type'],
                    use_auth=use_auth
                )
                
                if not vote_success:
                    print("❌ Failed to submit vote after interactions")
                    self.test_results.append({"name": "Independent Content Interactions - Vote After", "status": "FAIL", "details": "Failed to submit vote after interactions"})
                    return False
                
                print("✅ Successfully voted after setting interactions")
                self.test_results.append({"name": "Independent Content Interactions - Vote After", "status": "PASS", "details": "Successfully voted after setting interactions"})
                
                # Get a new voting pair to verify persistence
                print("\nGetting new voting pair to verify interaction persistence...")
                new_pair_success, new_pair = self.test_get_voting_pair(use_auth=use_auth)
                
                if not new_pair_success:
                    print("❌ Failed to get new voting pair")
                    self.test_results.append({"name": "Independent Content Interactions - Persistence", "status": "FAIL", "details": "Failed to get new voting pair"})
                    return False
                
                # Check if previous interactions persist
                old_status1_success, old_status1 = self.test_get_content_user_status(
                    content_id1, 
                    use_auth=use_auth
                )
                
                old_status2_success, old_status2 = self.test_get_content_user_status(
                    content_id2, 
                    use_auth=use_auth
                )
                
                if not old_status1_success or not old_status2_success:
                    print("❌ Failed to get old content status")
                    self.test_results.append({"name": "Independent Content Interactions - Persistence", "status": "FAIL", "details": "Failed to get old content status"})
                    return False
                
                if old_status1.get('not_interested', False) and old_status2.get('wants_to_watch', False):
                    print("✅ Verified interaction persistence after voting and getting new pair:")
                    print(f"  Item 1 ({pair['item1']['title']}): Still 'not interested'")
                    print(f"  Item 2 ({pair['item2']['title']}): Still 'want to watch'")
                    self.test_results.append({"name": "Independent Content Interactions - Persistence", "status": "PASS", "details": "Successfully verified interaction persistence"})
                    return True
                else:
                    print("❌ Failed to verify interaction persistence")
                    print(f"  Item 1 not_interested status: {old_status1.get('not_interested', False)}")
                    print(f"  Item 2 want_to_watch status: {old_status2.get('wants_to_watch', False)}")
                    self.test_results.append({"name": "Independent Content Interactions - Persistence", "status": "FAIL", "details": "Failed to verify interaction persistence"})
                    return False
            else:
                print("❌ Failed to verify interaction change")
                print(f"  Item 1 not_interested status: {status1_after.get('not_interested', False)}")
                print(f"  Item 2 want_to_watch status: {status2_after.get('wants_to_watch', False)}")
                self.test_results.append({"name": "Independent Content Interactions - Change Verification", "status": "FAIL", "details": "Failed to verify interaction change"})
                return False
        else:
            print("❌ Failed to verify independent interactions")
            print(f"  Item 1 watched status: {status1.get('has_watched', False)}")
            print(f"  Item 2 want to watch status: {status2.get('wants_to_watch', False)}")
            self.test_results.append({"name": "Independent Content Interactions", "status": "FAIL", "details": "Failed to verify independent interactions"})
            return False

    def run_tests(self):
        """Run all tests for independent content interactions"""
        print("\n🚀 Starting Independent Content Interactions Tests\n")
        
        # Test with authenticated user
        print("\n📋 Testing with authenticated user")
        auth_success, _ = self.test_user_registration()
        if auth_success:
            self.test_independent_content_interactions(use_auth=True)
        
        # Test with guest session
        print("\n📋 Testing with guest session")
        self.auth_token = None  # Clear auth token to force guest session
        session_success, _ = self.test_create_session()
        if session_success:
            self.test_independent_content_interactions(use_auth=False)
        
        # Print results
        print(f"\n📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        
        # Print detailed results
        print("\n📋 Test Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = IndependentContentInteractionsTester()
    success = tester.run_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())