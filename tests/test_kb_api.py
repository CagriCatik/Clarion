import requests
import os

BASE_URL = "http://localhost:8000"

def test_list_documents():
    print("Testing GET /v1/kb/documents...")
    try:
        response = requests.get(f"{BASE_URL}/v1/kb/documents")
        if response.status_code == 200:
            print("SUCCESS: Retrieved documents.")
            print(response.json())
        else:
            print(f"FAILURE: Status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"ERROR: {e}")

def test_index_document():
    print("\nTesting POST /v1/kb/index...")
    # Create a dummy file
    with open("test_kb_doc.txt", "w") as f:
        f.write("This is a test document for the Clarion Knowledge Base.")

    try:
        with open("test_kb_doc.txt", 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/v1/kb/index", files=files)
            
        if response.status_code == 200:
            print("SUCCESS: Indexed document.")
            print(response.json())
        else:
            print(f"FAILURE: Status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if os.path.exists("test_kb_doc.txt"):
            try:
                os.remove("test_kb_doc.txt")
            except PermissionError:
                print("WARNING: Could not delete test file (PermissionError).")

if __name__ == "__main__":
    test_list_documents()
    test_index_document()
    test_list_documents() # Check if it appears
