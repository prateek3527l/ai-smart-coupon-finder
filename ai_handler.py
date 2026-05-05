import os
import requests
from typing import Optional

def get_ai_response(prompt: str) -> Optional[str]:
    """
    Get AI response from Google Gemini API
    
    Parameters:
    prompt (str): The prompt to send to Gemini
    
    Returns:
    str or None: AI response text or None if failed
    """
    
    # Get API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        return None
    
    # Construct API endpoint
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Prepare request payload
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.9,
            "topK": 40,
            "maxOutputTokens": 500
        }
    }
    
    # Set headers
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Send POST request
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=6
        )
        
        # Check if status code is OK
        if response.status_code != 200:
            print(f"❌ API Error: Status {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        # Parse response
        data = response.json()
        
        # Safely extract text from response - UPDATED
        try:
            # Check if candidates exist and not empty
            candidates = data.get("candidates", [])
            if not candidates:
                print("⚠️ No candidates in API response")
                return None
            
            # Get first candidate
            first_candidate = candidates[0]
            content = first_candidate.get("content", {})
            parts = content.get("parts", [])
            
            if not parts:
                print("⚠️ No parts in API response")
                return None
            
            # Get text from first part
            text_response = parts[0].get("text")
            
            if text_response:
                return text_response.strip()
            else:
                print("⚠️ No text found in API response")
                return None
                
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return None
            
    except requests.Timeout:
        print("❌ Timeout error: API request took too long")
        return None
        
    except requests.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return None
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None