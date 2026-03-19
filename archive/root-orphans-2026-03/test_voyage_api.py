import requests
import os

VOYAGE_API_KEY = "pa-7E7GHt9qJqXDBYiUhtDOdHLOZHbWGcGbDvnKJ7G9x24"
EMBEDDING_MODEL = "voyage-3"

print("Testing Voyage AI REST API...")

try:
    response = requests.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {VOYAGE_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "input": ["This is a test sentence"],
            "model": EMBEDDING_MODEL,
            "input_type": "document"
        },
        timeout=30
    )

    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text[:500]}")

    if response.status_code == 200:
        result = response.json()
        embedding = result["data"][0]["embedding"]
        print(f"✅ SUCCESS! Embedding has {len(embedding)} dimensions")
        print(f"First 5 values: {embedding[:5]}")
    else:
        print(f"❌ FAILED: {response.status_code}")

except Exception as e:
    print(f"❌ ERROR: {e}")
