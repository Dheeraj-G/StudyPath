"""
Image Parser Agent using LangChain + Groq
Loads images from GCS (or preprocessed URLs), optionally preprocesses, then runs LLM.
"""

from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from PIL import Image, ImageOps, ImageFilter
import io
import httpx
import os

from config.settings import get_settings
from services.gcs_service import gcs_service


def _preprocess_image_bytes(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.grayscale(img)
    img = img.filter(ImageFilter.SHARPEN)
    max_w = 1600
    if img.width > max_w:
        ratio = max_w / float(img.width)
        new_h = int(img.height * ratio)
        img = img.resize((max_w, new_h))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


class ImageParserAgent:
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatGroq(
            api_key=self.settings.GROQ_API_KEY,
            model=self.settings.GROQ_IMAGE_MODEL,
            temperature=0.1,
        )
        self.prompt = ChatPromptTemplate.from_template(
            (
                "You analyze images for learning. Given signed image URLs, extract study cues. "
                "Return JSON with: objects (list), text_snippets (list), diagrams (list), concepts (list), description (string).\n\n"
                "Image URLs: {signed_urls}"
            )
        )

    async def parse(self, user_id: str, image_paths_or_urls: List[str]) -> Dict[str, Any]:
        # Ensure inputs are signed URLs; if given GCS paths, create URLs and also upload preprocessed version
        signed_urls: List[str] = []
        for item in image_paths_or_urls:
            if item.startswith("http"):
                signed_urls.append(item)
            else:
                try:
                    # Download original
                    url = gcs_service.create_signed_download_url(item)
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(url, timeout=60.0)
                        resp.raise_for_status()
                        pre = _preprocess_image_bytes(resp.content)
                    # Upload preprocessed image
                    base = os.path.basename(item)
                    processed_path = f"users/{user_id}/processed/images/{base}.png"
                    gcs_service.upload_file_directly(processed_path, pre, "image/png")
                    signed_urls.append(gcs_service.create_signed_download_url(processed_path))
                except Exception:
                    # fallback to original
                    signed_urls.append(gcs_service.create_signed_download_url(item))

        chain = self.prompt | self.llm
        response = await chain.ainvoke({"signed_urls": signed_urls})
        return {
            "type": "image",
            "urls": signed_urls,
            "raw": response.content,
        }


