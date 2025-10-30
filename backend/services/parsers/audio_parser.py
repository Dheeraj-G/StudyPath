"""
Audio Parser Agent using LangChain + Groq
Accepts audio GCS paths or signed URLs and prompts an LLM for outline/notes.
"""

from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config.settings import get_settings
from services.gcs_service import gcs_service


class AudioParserAgent:
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatGroq(
            api_key=self.settings.GROQ_API_KEY,
            model=self.settings.GROQ_AUDIO_MODEL,
            temperature=0.2,
        )
        self.prompt = ChatPromptTemplate.from_template(
            (
                "You are an academic note taker. Given signed audio URLs, return JSON with: "
                "transcript_outline (list of bullets), key_takeaways (list), action_items (list), speakers (list).\n\n"
                "Audio URLs: {signed_urls}"
            )
        )

    async def parse(self, audio_paths_or_urls: List[str]) -> Dict[str, Any]:
        signed_urls: List[str] = []
        for item in audio_paths_or_urls:
            if item.startswith("http"):
                signed_urls.append(item)
            else:
                signed_urls.append(gcs_service.create_signed_download_url(item))
        chain = self.prompt | self.llm
        response = await chain.ainvoke({"signed_urls": signed_urls})
        return {
            "type": "audio",
            "urls": signed_urls,
            "raw": response.content,
        }


