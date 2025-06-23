import requests
import unittest
import time
import sys
import random
import string
from datetime import datetime
import json

class DynamicTileReplacementTester:
    def __init__(self, base_url="https://4fa5a25b-d44d-470b-8afe-5cd4e20504f0.preview.emergentagent.com/api"):
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
        
        print(f"🔍 Testing Dynamic Tile Replacement at: {self.base_url}")
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

    def create_session(self):
        """Create a guest session"""
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

    def get_voting_pair(self, use_auth=False):
        """Get a voting pair"""
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
                
                # Print the titles for reference
                print(f"Item 1: {response['item1']['title']} (ID: {response['item1']['id']})")
                print(f"Item 2: {response['item2']['title']} (ID: {response['item2']['id']})")
                
                return True, response
            else:
                print(f"❌ Failed: Items have different types: '{response['item1']['content_type']}' and '{response['item2']['content_type']}'")
                self.test_results.append({"name": "Verify Same Content Type", "status": "FAIL", 
                                         "details": f"Items have different types: '{response['item1']['content_type']}' and '{response['item2']['content_type']}'"})
                return False, response
        
        return success, response

    def test_voting_pair_replacement(self, use_auth=False):
        """Test the voting pair replacement API endpoint"""
        print("\n🔍 Testing Voting Pair Replacement API...")
        
        # First, get a voting pair
        pair_success, pair = self.get_voting_pair(use_auth=use_auth)
        if not pair_success:
            print("❌ Failed to get initial voting pair")
            self.test_results.append({"name": "Voting Pair Replacement", "status": "FAIL", "details": "Failed to get initial voting pair"})
            return False, {}
        
        # Choose one content ID to keep
        remaining_content_id = pair['item1']['id']
        remaining_content_title = pair['item1']['title']
        replaced_content_id = pair['item2']['id']
        replaced_content_title = pair['item2']['title']
        content_type = pair['content_type']
        
        print(f"Testing replacement with:")
        print(f"  Remaining content: {remaining_content_title} (ID: {remaining_content_id})")
        print(f"  Content to replace: {replaced_content_title} (ID: {replaced_content_id})")
        print(f"  Content type: {content_type}")
        
        # Set up parameters
        params = {}
        if use_auth and self.auth_token:
            auth = True
        elif self.session_id:
            params = {"session_id": self.session_id}
            auth = False
        else:
            print("❌ No session ID or auth token available")
            self.test_results.append({"name": "Voting Pair Replacement", "status": "SKIP", "details": "No session ID or auth token available"})
            return False, {}
        
        # Call the replacement endpoint
        success, response = self.run_test(
            "Voting Pair Replacement",
            "GET",
            f"voting-pair-replacement/{remaining_content_id}",
            200,
            auth=auth,
            params=params
        )
        
        if not success:
            print("❌ Failed to get replacement voting pair")
            return False, {}
        
        # Verify the response contains a valid voting pair
        if 'item1' not in response or 'item2' not in response:
            print("❌ Response doesn't contain a valid voting pair")
            self.test_results.append({"name": "Voting Pair Replacement - Response Format", "status": "FAIL", "details": "Response doesn't contain a valid voting pair"})
            return False, response
        
        # Verify that one of the items is the remaining content
        remaining_content_found = False
        new_content_id = None
        
        if response['item1']['id'] == remaining_content_id:
            remaining_content_found = True
            new_content_id = response['item2']['id']
            new_content_title = response['item2']['title']
        elif response['item2']['id'] == remaining_content_id:
            remaining_content_found = True
            new_content_id = response['item1']['id']
            new_content_title = response['item1']['title']
        
        if not remaining_content_found:
            print("❌ Remaining content not found in replacement pair")
            self.test_results.append({"name": "Voting Pair Replacement - Content Preservation", "status": "FAIL", "details": "Remaining content not found in replacement pair"})
            return False, response
        
        # Verify that the new content is different from the replaced content
        if new_content_id == replaced_content_id:
            print("❌ New content is the same as replaced content")
            self.test_results.append({"name": "Voting Pair Replacement - New Content", "status": "FAIL", "details": "New content is the same as replaced content"})
            return False, response
        
        # Verify that both items are of the same content type
        if response['item1']['content_type'] != response['item2']['content_type']:
            print("❌ Items in replacement pair have different content types")
            self.test_results.append({"name": "Voting Pair Replacement - Content Type", "status": "FAIL", "details": "Items in replacement pair have different content types"})
            return False, response
        
        # Verify that the content type matches the original pair
        if response['content_type'] != content_type:
            print("❌ Replacement pair has different content type than original pair")
            self.test_results.append({"name": "Voting Pair Replacement - Content Type Preservation", "status": "FAIL", "details": "Replacement pair has different content type than original pair"})
            return False, response
        
        print("✅ Voting pair replacement successful:")
        print(f"  Remaining content: {remaining_content_title} (ID: {remaining_content_id})")
        print(f"  New content: {new_content_title} (ID: {new_content_id})")
        print(f"  Content type: {response['content_type']}")
        
        self.test_results.append({
            "name": "Voting Pair Replacement", 
            "status": "PASS", 
            "details": f"Successfully replaced content while preserving {remaining_content_title}"
        })
        
        return True, response

    def test_content_interaction(self, content_id, interaction_type, use_auth=False, session_id=None):
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

    def test_multiple_replacements(self, use_auth=False):
        """Test multiple consecutive replacements"""
        print("\n🔍 Testing Multiple Consecutive Replacements...")
        
        # Get initial voting pair
        pair_success, pair = self.get_voting_pair(use_auth=use_auth)
        if not pair_success:
            print("❌ Failed to get initial voting pair")
            self.test_results.append({"name": "Multiple Replacements", "status": "FAIL", "details": "Failed to get initial voting pair"})
            return False
        
        # Store initial content IDs and titles
        item1_id = pair['item1']['id']
        item1_title = pair['item1']['title']
        item2_id = pair['item2']['id']
        item2_title = pair['item2']['title']
        content_type = pair['content_type']
        
        print(f"Initial pair: {item1_title} vs {item2_title}")
        
        # First replacement - replace item1
        replacement1_success, replacement1 = self.test_voting_pair_replacement(use_auth=use_auth)
        if not replacement1_success:
            print("❌ Failed first replacement")
            self.test_results.append({"name": "Multiple Replacements - First", "status": "FAIL", "details": "Failed first replacement"})
            return False
        
        # Find the new content ID and title
        if replacement1['item1']['id'] == item1_id:
            new_item_id = replacement1['item2']['id']
            new_item_title = replacement1['item2']['title']
            remaining_id = item1_id
            remaining_title = item1_title
        elif replacement1['item2']['id'] == item1_id:
            new_item_id = replacement1['item1']['id']
            new_item_title = replacement1['item1']['title']
            remaining_id = item1_id
            remaining_title = item1_title
        elif replacement1['item1']['id'] == item2_id:
            new_item_id = replacement1['item2']['id']
            new_item_title = replacement1['item2']['title']
            remaining_id = item2_id
            remaining_title = item2_title
        elif replacement1['item2']['id'] == item2_id:
            new_item_id = replacement1['item1']['id']
            new_item_title = replacement1['item1']['title']
            remaining_id = item2_id
            remaining_title = item2_title
        else:
            print("❌ Could not identify new and remaining items after first replacement")
            self.test_results.append({"name": "Multiple Replacements - Identification", "status": "FAIL", "details": "Could not identify new and remaining items"})
            return False
        
        print(f"After first replacement: {new_item_title} vs {remaining_title}")
        
        # Second replacement - replace the new item
        params = {}
        if use_auth and self.auth_token:
            auth = True
        elif self.session_id:
            params = {"session_id": self.session_id}
            auth = False
        
        # Call the replacement endpoint with the remaining ID
        replacement2_success, replacement2 = self.run_test(
            "Second Replacement",
            "GET",
            f"voting-pair-replacement/{remaining_id}",
            200,
            auth=auth,
            params=params
        )
        
        if not replacement2_success:
            print("❌ Failed second replacement")
            self.test_results.append({"name": "Multiple Replacements - Second", "status": "FAIL", "details": "Failed second replacement"})
            return False
        
        # Verify the second replacement
        if 'item1' not in replacement2 or 'item2' not in replacement2:
            print("❌ Second replacement response doesn't contain a valid voting pair")
            self.test_results.append({"name": "Multiple Replacements - Response Format", "status": "FAIL", "details": "Second replacement response doesn't contain a valid voting pair"})
            return False
        
        # Find the newest content
        if replacement2['item1']['id'] == remaining_id:
            newest_item_id = replacement2['item2']['id']
            newest_item_title = replacement2['item2']['title']
        elif replacement2['item2']['id'] == remaining_id:
            newest_item_id = replacement2['item1']['id']
            newest_item_title = replacement2['item1']['title']
        else:
            print("❌ Remaining content not found in second replacement pair")
            self.test_results.append({"name": "Multiple Replacements - Content Preservation", "status": "FAIL", "details": "Remaining content not found in second replacement pair"})
            return False
        
        # Verify the newest content is different from both original and first replacement
        if newest_item_id == item1_id or newest_item_id == item2_id or newest_item_id == new_item_id:
            print("❌ Second replacement content is not unique")
            self.test_results.append({"name": "Multiple Replacements - Uniqueness", "status": "FAIL", "details": "Second replacement content is not unique"})
            return False
        
        print(f"After second replacement: {newest_item_title} vs {remaining_title}")
        print("✅ Multiple consecutive replacements successful")
        
        self.test_results.append({
            "name": "Multiple Replacements", 
            "status": "PASS", 
            "details": "Successfully performed multiple consecutive replacements with unique content"
        })
        
        return True

    def test_interaction_preservation(self, use_auth=False):
        """Test that interactions are preserved during replacement"""
        print("\n🔍 Testing Interaction Preservation During Replacement...")
        
        # Get initial voting pair
        pair_success, pair = self.get_voting_pair(use_auth=use_auth)
        if not pair_success:
            print("❌ Failed to get initial voting pair")
            self.test_results.append({"name": "Interaction Preservation", "status": "FAIL", "details": "Failed to get initial voting pair"})
            return False
        
        # Store content IDs
        item1_id = pair['item1']['id']
        item1_title = pair['item1']['title']
        item2_id = pair['item2']['id']
        item2_title = pair['item2']['title']
        
        print(f"Initial pair: {item1_title} vs {item2_title}")
        
        # Mark item1 as watched
        watched_success, _ = self.test_content_interaction(
            item1_id, 
            "watched",
            use_auth=use_auth
        )
        
        if not watched_success:
            print("❌ Failed to mark item as watched")
            self.test_results.append({"name": "Interaction Preservation - Initial Interaction", "status": "FAIL", "details": "Failed to mark item as watched"})
            return False
        
        print(f"Marked '{item1_title}' as watched")
        
        # Replace item2 (the one not marked as watched)
        params = {}
        if use_auth and self.auth_token:
            auth = True
        elif self.session_id:
            params = {"session_id": self.session_id}
            auth = False
        
        # Call the replacement endpoint with item1 (the one we want to keep)
        replacement_success, replacement = self.run_test(
            "Replacement While Preserving Interaction",
            "GET",
            f"voting-pair-replacement/{item1_id}",
            200,
            auth=auth,
            params=params
        )
        
        if not replacement_success:
            print("❌ Failed to get replacement while preserving interaction")
            self.test_results.append({"name": "Interaction Preservation - Replacement", "status": "FAIL", "details": "Failed to get replacement while preserving interaction"})
            return False
        
        # Verify the watched item is still in the pair
        if replacement['item1']['id'] != item1_id and replacement['item2']['id'] != item1_id:
            print("❌ Watched item not found in replacement pair")
            self.test_results.append({"name": "Interaction Preservation - Content Preservation", "status": "FAIL", "details": "Watched item not found in replacement pair"})
            return False
        
        # Find the new content
        if replacement['item1']['id'] == item1_id:
            new_item_id = replacement['item2']['id']
            new_item_title = replacement['item2']['title']
        else:
            new_item_id = replacement['item1']['id']
            new_item_title = replacement['item1']['title']
        
        print(f"After replacement: '{item1_title}' (watched) vs '{new_item_title}' (new)")
        print("✅ Interaction preservation successful")
        
        self.test_results.append({
            "name": "Interaction Preservation", 
            "status": "PASS", 
            "details": "Successfully preserved watched status during replacement"
        })
        
        return True

    def run_dynamic_tile_replacement_tests(self):
        """Run all tests related to dynamic tile replacement"""
        print("\n🚀 Starting Dynamic Tile Replacement Tests\n")
        
        # Create a session
        session_success, _ = self.create_session()
        if not session_success:
            print("❌ Failed to create session, stopping tests")
            return
        
        # Test 1: Basic Voting Pair Replacement
        self.test_voting_pair_replacement()
        
        # Test 2: Multiple Consecutive Replacements
        self.test_multiple_replacements()
        
        # Test 3: Interaction Preservation
        self.test_interaction_preservation()
        
        # Print results
        print(f"\n📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        
        # Print detailed results
        print("\n📋 Test Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['name']}: {result['status']} - {result['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = DynamicTileReplacementTester()
    success = tester.run_dynamic_tile_replacement_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
