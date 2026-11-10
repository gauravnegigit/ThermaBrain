import os
import hashlib
import json
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import pypdf  

from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Suppress the Windows symlink warning noise completely
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "true"

# ==========================================
# 1. PATH RESOLUTION & SETUP
# ==========================================
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent 
load_dotenv(project_root / ".env")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "fde-sop-index-gemini"
existing_index = pc.Index(index_name)

# 2. Initialize Google GenAI Embeddings (e.g., text-embedding-004)
# Make sure GEMINI_API_KEY is set in your environment variables
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001" , output_dimensionality=1536)

# 3. Connect LangChain to the existing Pinecone index
vector_store = PineconeVectorStore(
    index=existing_index,
    embedding=embeddings,
)

# 4. Prepare new documents to add
pdf_docs = []
doc_path = project_root/"data"/"policy"/"Temperature.pdf"

text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)
try:
    with open(doc_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text and page_text.strip():
                pdf_docs.append(Document(page_content=page_text, metadata={"page_number": page_num + 1}))
    raw_chunks = text_splitter.split_documents(pdf_docs)
except Exception as e:
    print(f"  ❌ Error parsing PDF {doc_path.name}: {e}")

chunks = []
for chunk in raw_chunks:
    clean_text = chunk.page_content.strip()
    if clean_text:
        chunk.page_content = clean_text
        chunks.append(chunk)


batch_size = 100
total_chunks = len(chunks)

print(f"  📤 Upserting {total_chunks} chunk(s) in batches of {batch_size}...")

explicit_ids = []
for idx, chunk in enumerate(chunks):
    chunk.metadata["source_file"] = "Temperature.pdf"
    chunk.metadata["file_format"] = doc_path.suffix.replace(".", "").upper()
    chunk.metadata["document_type"] = "Compliance Asset"
    explicit_ids.append(f"Temperature.pdf-chunk-{idx}")

for i in range(0, total_chunks, batch_size):
    batch_docs = chunks[i : i + batch_size]
    batch_ids = explicit_ids[i : i + batch_size]
    vector_store.add_documents(documents=batch_docs, ids=batch_ids)