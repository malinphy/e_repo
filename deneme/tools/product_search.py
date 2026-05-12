import os
import requests
import serpapi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

def search_walmart(query):
    """Searches Walmart for a product using SerpApi."""
    if not SERPAPI_KEY:
        return {"error": "SerpApi key not found"}
    
    params = {
        "engine": "walmart",
        "q": query,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        return response.json().get("organic_results", [])[:3]
    except Exception as e:
        return {"error": str(e)}

def search_amazon(query):
    """Searches Amazon for a product using the official SerpApi client."""
    if not SERPAPI_KEY:
        return {"error": "SerpApi key not found"}
    
    try:
        client = serpapi.Client(api_key=SERPAPI_KEY)
        results = client.search({
            "engine": "amazon",
            "q": query
        })
        # Use 'shopping_results' for Amazon
        return results.get("shopping_results", [])[:3]
    except Exception as e:
        return {"error": str(e)}

def search_ebay(query):
    """Searches eBay for a product using SerpApi."""
    if not SERPAPI_KEY:
        return {"error": "SerpApi key not found"}
    
    params = {
        "engine": "ebay",
        "_nkw": query,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        return response.json().get("organic_results", [])[:3]
    except Exception as e:
        return {"error": str(e)}

def compare_prices(query):
    """Fetches results from all three platforms and returns a combined comparison."""
    results = {
        "walmart": search_walmart(query),
        "amazon": search_amazon(query),
        "ebay": search_ebay(query)
    }
    return results

if __name__ == "__main__":
    # Test script
    import sys
    test_query = sys.argv[1] if len(sys.argv) > 1 else "coffee machine"
    print(f"Searching for: {test_query}...")
    comparison = compare_prices(test_query)
    print(comparison)
