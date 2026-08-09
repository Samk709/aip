import requests
import time
import os

BASE_URL = "http://localhost:5000"

def run_tests():
    print("Starting Automated RAG Backend Tests...")
    
    # Wait for server to be up
    for _ in range(5):
        try:
            res = requests.get(f"{BASE_URL}/api/health")
            if res.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            
    print("[1] Server is up and running.")

    # 1. Anonymous Login to get Token
    res = requests.post(f"{BASE_URL}/api/auth/anonymous")
    assert res.status_code == 200, f"Login failed: {res.text}"
    data = res.json()
    token = data["token"]
    user_id = data["user_id"]
    print(f"[2] Authenticated as Anonymous User (ID: {user_id})")
    
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create a dummy document to upload
    test_filepath = "test_therapy_journal.txt"
    with open(test_filepath, "w") as f:
        f.write("Journal Entry: I have been feeling very stressed about my upcoming exams. I love eating bananas to calm down.")
    
    # 3. Upload Document
    with open(test_filepath, "rb") as f:
        files = {"document": f}
        upload_res = requests.post(f"{BASE_URL}/api/chat/upload", headers=headers, files=files)
        
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    assert upload_data.get("success") == True
    print(f"[3] Document successfully uploaded to Gemini: {upload_data.get('filename')} (URI: {upload_data.get('file_uri')})")

    # 4. Chat and reference the document
    chat_payload = {
        "user_id": user_id,
        "message": "Based on the journal entry I just uploaded, what do I eat to calm down? Please answer briefly."
    }
    
    print("[4] Prompting AI with context...")
    chat_res = requests.post(f"{BASE_URL}/api/chat", headers=headers, json=chat_payload)
    assert chat_res.status_code == 200, f"Chat failed: {chat_res.text}"
    
    chat_data = chat_res.json()
    reply = chat_data.get("reply", "")
    print(f"[5] AI Reply Received: \n{reply}")
    
    if "banana" in reply.lower():
        print("✅ SUCCESS: The AI accurately read context from the uploaded document!")
    else:
        print("❌ WARNING: The AI did not mention bananas. RAG might not have injected the file correctly.")
        
    # Cleanup
    if os.path.exists(test_filepath):
        os.remove(test_filepath)
        
if __name__ == "__main__":
    run_tests()
