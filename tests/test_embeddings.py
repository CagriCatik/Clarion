import requests
import json

def test_embedding(model_name="nomic-embed-text:latest"):
    url = "http://localhost:11434/api/embeddings"
    payload = {
        "model": model_name,
        "prompt": "This is a test sentence to check embeddings."
    }
    
    print(f"Testing embedding for model: {model_name}")
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("SUCCESS: Embeddings generated.")
            # print(response.json())
        else:
            print(f"FAILURE: Status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_embedding()
