#!/usr/bin/env python3
"""
Investigate why Oppenheimer poster is not displaying
Check the specific poster URL and test its accessibility
"""

import pymongo
import requests
from urllib.parse import urlparse

def investigate_oppenheimer_poster():
    print("🔍 Investigating Oppenheimer Poster Loading Issue")
    print("=" * 55)
    
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["movie_preferences_db"]
    
    # Find Oppenheimer content
    oppenheimer = db.content.find_one({
        "title": {"$regex": "Oppenheimer", "$options": "i"},
        "year": "2023"
    })
    
    if oppenheimer:
        print(f"📋 Found Oppenheimer:")
        print(f"   Title: {oppenheimer.get('title', 'Unknown')}")
        print(f"   ID: {oppenheimer.get('id', 'Unknown')}")
        print(f"   Year: {oppenheimer.get('year', 'Unknown')}")
        print(f"   Type: {oppenheimer.get('content_type', 'Unknown')}")
        print(f"   Genre: {oppenheimer.get('genre', 'Unknown')}")
        print(f"   Poster URL: {oppenheimer.get('poster', 'None')}")
        
        poster_url = oppenheimer.get('poster')
        if poster_url:
            print(f"\n🌐 Testing Oppenheimer poster URL...")
            test_poster_url_detailed(poster_url)
        else:
            print(f"\n❌ No poster URL found for Oppenheimer!")
            
        return oppenheimer
    else:
        print("❌ Oppenheimer not found in database")
        
        # Try to find any Oppenheimer content
        all_oppenheimer = list(db.content.find({"title": {"$regex": "Oppenheimer", "$options": "i"}}))
        if all_oppenheimer:
            print(f"\n📋 Found {len(all_oppenheimer)} Oppenheimer-related content:")
            for item in all_oppenheimer:
                print(f"   - {item.get('title', 'Unknown')} ({item.get('year', 'Unknown')})")
        
        return None

def test_poster_url_detailed(url):
    """Detailed test of poster URL with comprehensive checks"""
    print(f"   🔗 URL: {url}")
    
    # Parse URL
    try:
        parsed = urlparse(url)
        print(f"   📡 Domain: {parsed.netloc}")
        print(f"   🔒 Scheme: {parsed.scheme}")
    except Exception as e:
        print(f"   ❌ URL parsing error: {e}")
        return False
    
    # Test with different methods
    methods_to_try = [
        ("HEAD request", lambda: requests.head(url, timeout=10, allow_redirects=True)),
        ("GET request", lambda: requests.get(url, timeout=10, allow_redirects=True))
    ]
    
    for method_name, method_func in methods_to_try:
        try:
            print(f"\n   🧪 Testing with {method_name}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = method_func()
            
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📄 Content-Type: {response.headers.get('content-type', 'Not specified')}")
            print(f"   📏 Content-Length: {response.headers.get('content-length', 'Not specified')}")
            
            if 'content-type' in response.headers:
                content_type = response.headers['content-type'].lower()
                if 'image' in content_type:
                    print(f"   ✅ Valid image content detected")
                else:
                    print(f"   ⚠️  Not image content: {content_type}")
            
            if response.status_code == 200:
                print(f"   ✅ {method_name} successful")
                return True
            elif response.status_code == 403:
                print(f"   🚫 Forbidden (403) - May be CORS or access restriction")
            elif response.status_code == 404:
                print(f"   ❌ Not Found (404) - URL is broken")
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout - Server not responding")
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Connection Error - Cannot reach server")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {str(e)}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {str(e)}")
    
    return False

def check_frontend_console_errors():
    """Check if there might be frontend console errors"""
    print(f"\n🖥️  Frontend Debugging Checklist:")
    print(f"   1. Open browser developer tools (F12)")
    print(f"   2. Go to Console tab")
    print(f"   3. Look for image loading errors like:")
    print(f"      - CORS errors")
    print(f"      - Mixed content warnings (HTTP vs HTTPS)")
    print(f"      - 404 Not Found errors")
    print(f"      - CSP (Content Security Policy) violations")
    print(f"   4. Go to Network tab and check failed image requests")

def suggest_fixes():
    """Suggest potential fixes based on common issues"""
    print(f"\n🔧 Potential Fixes to Try:")
    print(f"   1. **CORS Issues:**")
    print(f"      - Add crossorigin='anonymous' to img tags")
    print(f"      - Use proxy server for external images")
    print(f"   2. **Mixed Content:**")
    print(f"      - Ensure all poster URLs use HTTPS")
    print(f"   3. **CSP Violations:**")
    print(f"      - Update Content Security Policy to allow image sources")
    print(f"   4. **URL Expiration:**")
    print(f"      - Update poster URLs with fresh ones from OMDB")
    print(f"   5. **Image Format Issues:**")
    print(f"      - Convert to base64 data URLs")
    print(f"      - Use different image hosting")

if __name__ == "__main__":
    oppenheimer = investigate_oppenheimer_poster()
    check_frontend_console_errors()
    suggest_fixes()
    
    if oppenheimer and oppenheimer.get('poster'):
        print(f"\n💡 Next Steps:")
        print(f"   1. Test if the error handling is working by checking browser console")
        print(f"   2. Verify the image error handler is being triggered")
        print(f"   3. Check if there are any CORS or CSP issues blocking the image")
        print(f"   4. Consider using a different poster URL or image hosting approach")