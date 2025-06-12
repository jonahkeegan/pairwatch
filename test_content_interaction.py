import requests
import logging
import json
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("content_interaction_test")

# API base URL
BASE_URL = "https://bc399ce5-d614-4d4b-a2e3-afb7b5993410.preview.emergentagent.com/api"

def run_test(name, method, endpoint, expected_status, data=None, auth=False, auth_token=None, params=None):
    """Run a single API test"""
    url = f"{BASE_URL}/{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    # Add authorization header if needed
    if auth and auth_token:
        headers['Authorization'] = f'Bearer {auth_token}'
    
    logger.info(f"\n🔍 Testing {name}...")
    
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
            logger.info(f"✅ Passed - Status: {response.status_code}")
        else:
            logger.error(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
            if response.text:
                try:
                    error_detail = response.json()
                    logger.error(f"Error details: {json.dumps(error_detail, indent=2)}")
                except:
                    logger.error(f"Error response: {response.text}")

        try:
            return success, response.json() if response.text else {}
        except:
            return success, {}

    except Exception as e:
        logger.error(f"❌ Failed - Error: {str(e)}")
        return False, {}

def test_content_interaction_watched():
    """Test the specific scenario of marking content as watched"""
    logger.info("\n=== TESTING CONTENT INTERACTION 'WATCHED' FUNCTIONALITY ===")
    
    # Step 1: Register a new user
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    test_user = {
        "email": f"test_user_{timestamp}@example.com",
        "password": "TestPassword123!",
        "name": f"Test User {timestamp}"
    }
    
    logger.info("\n📋 Step 1: Register a new user")
    success, response = run_test(
        "User Registration",
        "POST",
        "auth/register",
        200,
        data=test_user
    )
    
    if not success or 'access_token' not in response:
        logger.error("❌ Failed to register user, stopping test")
        return False
    
    auth_token = response['access_token']
    user_id = response['user']['id']
    logger.info(f"✅ User registered with ID: {user_id}")
    
    # Step 2: Get content recommendations
    logger.info("\n📋 Step 2: Submit votes to get recommendations")
    
    # Submit 10 votes to get recommendations
    for i in range(10):
        # Get a voting pair
        success, pair = run_test(
            f"Get Voting Pair {i+1}",
            "GET",
            "voting-pair",
            200,
            auth=True,
            auth_token=auth_token
        )
        
        if not success:
            logger.error(f"❌ Failed to get voting pair on iteration {i+1}")
            return False
        
        # Submit a vote
        vote_data = {
            "winner_id": pair['item1']['id'],
            "loser_id": pair['item2']['id'],
            "content_type": pair['content_type']
        }
        
        success, _ = run_test(
            f"Submit Vote {i+1}",
            "POST",
            "vote",
            200,
            data=vote_data,
            auth=True,
            auth_token=auth_token
        )
        
        if not success:
            logger.error(f"❌ Failed to submit vote on iteration {i+1}")
            return False
        
        # Print progress
        if (i+1) % 5 == 0 or i == 9:
            logger.info(f"Progress: {i+1}/10 votes")
    
    # Wait for recommendations to be generated
    logger.info("Waiting 5 seconds for recommendations to be generated...")
    time.sleep(5)
    
    # Step 3: Get recommendations to find content IDs
    logger.info("\n📋 Step 3: Get recommendations to find content IDs")
    success, recommendations = run_test(
        "Get Recommendations",
        "GET",
        "recommendations",
        200,
        auth=True,
        auth_token=auth_token
    )
    
    if not success or not isinstance(recommendations, list) or len(recommendations) == 0:
        logger.error("❌ Failed to get recommendations or no recommendations available")
        return False
    
    logger.info(f"✅ Received {len(recommendations)} recommendations")
    
    # Step 4: Try to mark a specific content item as "watched"
    logger.info("\n📋 Step 4: Mark content as 'watched'")
    
    # Get content ID from first recommendation
    content_id = None
    for rec in recommendations:
        if 'imdb_id' in rec:
            # Get content details to get the content ID
            success, content_details = run_test(
                "Get Content Details",
                "GET",
                f"content/{rec['imdb_id']}",
                200,
                auth=True,
                auth_token=auth_token
            )
            
            if success and 'id' in content_details:
                content_id = content_details['id']
                break
    
    # If we couldn't get a content ID from recommendations, try getting a voting pair
    if not content_id:
        logger.info("Couldn't get content ID from recommendations, trying voting pair...")
        success, pair = run_test(
            "Get Voting Pair for Content ID",
            "GET",
            "voting-pair",
            200,
            auth=True,
            auth_token=auth_token
        )
        
        if success:
            content_id = pair['item1']['id']
    
    if not content_id:
        logger.error("❌ Failed to get a content ID to mark as watched")
        return False
    
    logger.info(f"✅ Using content ID: {content_id}")
    
    # Test with the exact payload format from the frontend
    interaction_data = {
        "content_id": content_id,
        "interaction_type": "watched"
    }
    
    success, response = run_test(
        "Mark Content as Watched",
        "POST",
        "content/interact",
        200,
        data=interaction_data,
        auth=True,
        auth_token=auth_token
    )
    
    if success:
        logger.info("✅ Successfully marked content as watched")
    else:
        logger.error("❌ Failed to mark content as watched")
        
        # Try with a different payload format to debug
        logger.info("\n📋 Debugging: Try different payload formats")
        
        # Try with additional fields
        debug_data = {
            "content_id": content_id,
            "interaction_type": "watched",
            "session_id": None,
            "priority": None
        }
        
        success, response = run_test(
            "Debug: Mark Content as Watched (with additional fields)",
            "POST",
            "content/interact",
            200,
            data=debug_data,
            auth=True,
            auth_token=auth_token
        )
        
        if success:
            logger.info("✅ Debug: Successfully marked content as watched with additional fields")
        else:
            logger.error("❌ Debug: Still failed with additional fields")
    
    # Step 5: Verify the interaction was recorded
    logger.info("\n📋 Step 5: Verify the interaction was recorded")
    success, status = run_test(
        "Get Content User Status",
        "GET",
        f"content/{content_id}/user-status",
        200,
        auth=True,
        auth_token=auth_token
    )
    
    if success:
        if 'interactions' in status and 'watched' in status['interactions']:
            logger.info("✅ Verified content was marked as watched")
            return True
        else:
            logger.error("❌ Content was not marked as watched in user status")
            logger.error(f"User status: {json.dumps(status, indent=2)}")
            return False
    else:
        logger.error("❌ Failed to get content user status")
        return False

if __name__ == "__main__":
    logger.info("Starting content interaction test...")
    test_content_interaction_watched()