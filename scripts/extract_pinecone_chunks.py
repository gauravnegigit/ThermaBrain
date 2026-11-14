import os
from pinecone import Pinecone
from dotenv import load_dotenv
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent 
load_dotenv(project_root / ".env")

# Connect to Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("fde-sop-index-gemini")

# Fetch all vector IDs (index.list yields lists of IDs automatically)
all_ids = []
for id_batch in index.list(limit=100):
    all_ids.extend(id_batch)

print(f"Total chunks found: {len(all_ids)}")

# Fetch vectors in batches
all_chunks = []

for i in range(0, len(all_ids), 100):
    batch_ids = all_ids[i:i + 100]
    response = index.fetch(ids=batch_ids)

    for vector_id, vector in response.vectors.items():
        all_chunks.append({
            "id": vector_id,
            "metadata": vector.metadata or {}  # Safely defaults to empty dict if None
        })

import json

with open("pinecone_chunks.json", "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, indent=4, ensure_ascii=False)

print("Exported to pinecone_chunks.json")

