def test_omdb_api_integration(self):
    """Test direct OMDB API integration with our API key"""
    print("\n🔍 Testing OMDB API Integration...")
    
    omdb_api_key = "33f2519b"  # Using the provided API key
    test_movie = "The Shawshank Redemption"
    
    try:
        # Test direct OMDB API access
        url = f"http://www.omdbapi.com/?apikey={omdb_api_key}&t={test_movie}&type=movie"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("Response") == "True":
                print(f"✅ OMDB API direct access successful")
                print(f"  Title: {data.get('Title')}")
                print(f"  Year: {data.get('Year')}")
                print(f"  IMDB Rating: {data.get('imdbRating')}")
                
                # Check if poster URL is valid
                if data.get("Poster") and data.get("Poster") != "N/A":
                    poster_url = data.get("Poster")
                    print(f"  Poster URL: {poster_url}")
                    
                    # Try to access the poster image
                    poster_response = requests.head(poster_url)
                    if poster_response.status_code == 200:
                        print(f"  ✅ Poster URL is accessible")
                        
                        # Check content type
                        content_type = poster_response.headers.get('Content-Type', '')
                        if 'image' in content_type.lower():
                            print(f"  ✅ Poster URL returns an image ({content_type})")
                        else:
                            print(f"  ⚠️ Poster URL does not return an image content type: {content_type}")
                    else:
                        print(f"  ❌ Poster URL is not accessible: {poster_response.status_code}")
                else:
                    print(f"  ⚠️ No poster URL available for this movie")
                
                self.test_results.append({
                    "name": "OMDB API Integration", 
                    "status": "PASS", 
                    "details": f"Successfully retrieved data for '{test_movie}'"
                })
                return True, data
            else:
                print(f"❌ OMDB API returned an error: {data.get('Error')}")
                self.test_results.append({
                    "name": "OMDB API Integration", 
                    "status": "FAIL", 
                    "details": f"API error: {data.get('Error')}"
                })
        else:
            print(f"❌ OMDB API request failed with status code: {response.status_code}")
            self.test_results.append({
                "name": "OMDB API Integration", 
                "status": "FAIL", 
                "details": f"Request failed with status code: {response.status_code}"
            })
    
    except Exception as e:
        print(f"❌ OMDB API test failed with error: {str(e)}")
        self.test_results.append({
            "name": "OMDB API Integration", 
            "status": "ERROR", 
            "details": str(e)
        })
    
    return False, {}
