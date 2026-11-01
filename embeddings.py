from typing import List
from langchain_core.embeddings import Embeddings
import requests

class GnaniEmbeddings(Embeddings):
    def __init__(self, api_key: str, api_url: str = "https://gnani.ai"):
        self.api_key = api_key
        self.api_url = api_url

    def _get_embedding(self, text: str) -> List[float]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"text": text}
        
        response = requests.post(self.api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Parse the vector array from Gnani's API response structure
        return response.json()["embedding"]