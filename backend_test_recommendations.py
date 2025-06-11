import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json

class RecommendationAPITester:
    def __init__(self, base_url="https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"):
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
        
        print(f"🔍 Testing API at: {self.base_url}")
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

    # Authentication Tests
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
        
        return success, response
    
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
        
        return success, response
    
    def test_generate_ml_recommendations(self):
        """Test generating ML-powered recommendations"""
        if not self.auth_token:
            print("❌ No auth token available")
            self.test_results.append({"name": "Generate ML Recommendations", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        success, response = self.run_test(
            "Generate ML Recommendations",
            "POST",
            "recommendations/generate",
            200,
            data={},
            auth=True
        )
        
        if success:
            print(f"✅ ML Recommendations generated:")
            print(f"  Message: {response.get('message', '')}")
            print(f"  Recommendations generated: {response.get('recommendations_generated', 0)}")
            print(f"  User profile strength: {response.get('user_profile_strength', 0)}")
            
            # Check recommendation categories
            if 'recommendation_categories' in response:
                categories = response['recommendation_categories']
                print(f"  High confidence recommendations: {categories.get('high_confidence', 0)}")
                print(f"  Medium confidence recommendations: {categories.get('medium_confidence', 0)}")
                print(f"  Exploratory recommendations: {categories.get('exploratory', 0)}")
            
            return True, response
        
        return False, response
    
    def test_get_watchlist(self, watchlist_type="user_defined"):
        """Test getting user watchlist"""
        if not self.auth_token:
            print("❌ No auth token available for watchlist")
            self.test_results.append({"name": f"Get Watchlist ({watchlist_type})", "status": "SKIP", "details": "No auth token available"})
            return False, {}
        
        success, response = self.run_test(
            f"Get Watchlist ({watchlist_type})",
            "GET",
            f"watchlist/{watchlist_type}",
            200,
            auth=True
        )
        
        if success:
            print(f"✅ Retrieved {watchlist_type} watchlist with {response.get('total_count', 0)} items")
            
            # Print watchlist items
            if response.get('items'):
                for i, item in enumerate(response['items']):
                    print(f"  {i+1}. {item['content']['title']} ({item['content']['year']})")
                    if watchlist_type == "algo_predicted" and "reasoning" in item:
                        print(f"     Reason: {item.get('reasoning')}")
            
            return True, response
        
        return False, response
    
    def test_initialize_content(self):
        """Test content initialization"""
        success, response = self.run_test(
            "Initialize Content",
            "POST",
            "initialize-content",
            200,
            data={}
        )
        
        return success, response
    
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
    
    def perform_multiple_interactions(self, num_interactions=10):
        """Perform multiple content interactions to build user profile"""
        print(f"\n🔄 Performing {num_interactions} content interactions to build user profile...")
        
        interactions_performed = 0
        
        for i in range(num_interactions):
            # Get a voting pair
            success, pair = self.test_get_voting_pair(use_auth=True)
            if not success:
                print(f"❌ Failed to get voting pair on iteration {i+1}")
                continue
            
            # Submit a vote
            vote_success, _ = self.test_submit_vote(
                pair['item1']['id'], 
                pair['item2']['id'],
                pair['content_type'],
                use_auth=True
            )
            
            if not vote_success:
                print(f"❌ Failed to submit vote on iteration {i+1}")
                continue
            
            # Add some content interactions (watched, want_to_watch)
            if i % 3 == 0:
                self.test_content_interaction(pair['item1']['id'], "watched", use_auth=True)
            elif i % 3 == 1:
                self.test_content_interaction(pair['item1']['id'], "want_to_watch", use_auth=True)
            
            interactions_performed += 1
            
            # Print progress
            if (i+1) % 2 == 0:
                print(f"Progress: {i+1}/{num_interactions} interactions")
        
        print(f"✅ Successfully completed {interactions_performed} interactions")
        return interactions_performed >= 10  # Need at least 10 interactions for ML recommendations
    
    def test_recommendation_flow(self):
        """Test the complete recommendation flow"""
        print("\n🔍 Testing ML Recommendation Flow")
        
        # Initialize content
        self.test_initialize_content()
        
        # Register a new user
        reg_success, _ = self.test_user_registration()
        if not reg_success:
            print("❌ Failed to register user, stopping recommendation flow tests")
            return False
        
        # Perform multiple interactions to build user profile
        if not self.perform_multiple_interactions(15):
            print("❌ Failed to perform enough interactions")
            return False
        
        # Generate ML recommendations
        gen_success, gen_response = self.test_generate_ml_recommendations()
        if not gen_success:
            print("❌ Failed to generate ML recommendations")
            return False
        
        # Get algo watchlist
        algo_success, algo_watchlist = self.test_get_watchlist("algo_predicted")
        if not algo_success:
            print("❌ Failed to get algo watchlist")
            return False
        
        # Check if recommendations were generated
        if not algo_watchlist.get('items'):
            print("❌ No recommendations in algo watchlist")
            return False
        
        print(f"✅ Successfully tested ML recommendation flow")
        print(f"✅ Generated {len(algo_watchlist.get('items', []))} ML recommendations")
        
        return True

def main():
    tester = RecommendationAPITester()
    success = tester.test_recommendation_flow()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())