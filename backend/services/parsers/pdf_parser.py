"""
PDF Parser Agent using LangChain + Groq
Loads PDFs from GCS paths, chunks text (~1000-token heuristic), extracts images,
preprocesses images, and runs LLM over chunks.
"""

from typing import List, Dict, Any, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pypdf import PdfReader
from PIL import Image, ImageOps, ImageFilter
import io
import httpx
import os
import asyncio

from config.settings import get_settings
from services.gcs_service import gcs_service
from services.firestore_service import firestore_service


def _chunk_text_by_words(text: str, words_per_chunk: int = 750) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), words_per_chunk):
        chunks.append(" ".join(words[i:i + words_per_chunk]))
    return chunks


def _preprocess_image(img: Image.Image) -> Image.Image:
    # Convert to grayscale, enhance contrast, sharpen, resize to max width 1600
    img = ImageOps.grayscale(img)
    img = img.filter(ImageFilter.SHARPEN)
    max_w = 1600
    if img.width > max_w:
        ratio = max_w / float(img.width)
        new_h = int(img.height * ratio)
        img = img.resize((max_w, new_h))
    return img


def _extract_images_from_pdf(reader: PdfReader) -> List[Image.Image]:
    images: List[Image.Image] = []
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        xobject = None
        if "/XObject" in resources:
            xobject = resources["/XObject"].get_object()
        if not xobject:
            continue
        for obj_name in xobject:
            obj = xobject[obj_name]
            if obj.get("/Subtype") == "/Image":
                try:
                    data = obj.get_data()
                    img = None
                    if obj.get("/ColorSpace") == "/DeviceRGB" and obj.get("/Filter") == "/DCTDecode":
                        img = Image.open(io.BytesIO(data))
                    else:
                        width = obj.get("/Width")
                        height = obj.get("/Height")
                        mode = "RGB"
                        img = Image.frombytes(mode, (width, height), data)
                    if img:
                        images.append(img)
                except Exception:
                    continue
    return images


class PDFParserAgent:
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatGroq(
            api_key=self.settings.GROQ_API_KEY,
            model=self.settings.GROQ_PDF_MODEL,
            temperature=0.2,
        )
        self.chunk_prompt = ChatPromptTemplate.from_template(
            (
                "You are a precise PDF study parser. Given a text chunk from a PDF, "
                "extract structured study info. Return JSON with: topics (list), key_points (list), "
                "summary (string), citations (list), difficulty_estimate (string).\n\n"
                "Chunk:\n{chunk}"
            )
        )

    async def _upload_and_sign_image(self, user_id: str, parent_file_id: str, img: Image.Image, base_name: str) -> Tuple[str, str]:
        processed = _preprocess_image(img)
        buf = io.BytesIO()
        processed.save(buf, format="PNG")
        buf.seek(0)
        file_path = f"users/{user_id}/processed/images/{base_name}.png"
        gcs_service.upload_file_directly(file_path, buf.getvalue(), "image/png")
        url = gcs_service.create_signed_download_url(file_path)
        # Track as a derived asset under the original upload so recursive removal sees it
        try:
            await firestore_service.add_derived_asset(
                user_id,
                parent_file_id,
                {
                    "asset_type": "image",
                    "origin": "pdf_extraction",
                    "gcs_path": file_path,
                    "signed_url": url,
                    "filename": base_name + ".png",
                },
            )
        except Exception:
            pass
        return file_path, url

    async def _process_single_pdf(self, user_id: str, file_path: str) -> Dict[str, Any]:
        # Download PDF via signed URL
        signed_url = gcs_service.create_signed_download_url(file_path)
        async with httpx.AsyncClient() as client:
            resp = await client.get(signed_url, timeout=60.0)
            resp.raise_for_status()
            pdf_bytes = resp.content

        reader = PdfReader(io.BytesIO(pdf_bytes))
        # Extract text
        all_text_parts: List[str] = []
        for page in reader.pages:
            try:
                all_text_parts.append(page.extract_text() or "")
            except Exception:
                all_text_parts.append("")
        full_text = "\n".join(all_text_parts)
        chunks = _chunk_text_by_words(full_text, 750)  # ~1000 tokens heuristic

        # Extract images and preprocess/upload
        extracted_images = _extract_images_from_pdf(reader)
        uploaded_images: List[Dict[str, str]] = []
        # Derive parent file_id from path: users/{uid}/uploads/{type}/{file_id}/{filename}
        parts = file_path.split("/")
        file_id = parts[5] if len(parts) >= 6 and parts[0] == "users" else "unknown"
        for idx, img in enumerate(extracted_images):
            try:
                pth, url = await self._upload_and_sign_image(user_id, file_id, img, base_name=f"{os.path.basename(file_path)}_{idx}")
                uploaded_images.append({"path": pth, "url": url})
            except Exception:
                continue

        # Run LLM on chunks sequentially with light concurrency
        async def run_chunk(chunk: str) -> str:
            chain = self.chunk_prompt | self.llm
            res = await chain.ainvoke({"chunk": chunk})
            return res.content

        semaphore = asyncio.Semaphore(3)

        async def bound_run(chunk: str) -> str:
            async with semaphore:
                return await run_chunk(chunk)

        llm_outputs = await asyncio.gather(*[bound_run(c) for c in chunks if c.strip()])

        return {
            "file_path": file_path,
            "chunks_processed": len(chunks),
            "llm_outputs": llm_outputs,
            "extracted_images": uploaded_images,
        }

    async def parse(self, user_id: str, pdf_paths: List[str]) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for path in pdf_paths:
            try:
                results.append(await self._process_single_pdf(user_id, path))
            except Exception as e:
                results.append({"file_path": path, "error": str(e)})
        # Aggregate image URLs for downstream image parser
        image_urls = []
        for r in results:
            for img in r.get("extracted_images", []):
                if "url" in img:
                    image_urls.append(img["url"])
        return {
            "type": "pdf",
            "results": results,
            "derived_image_urls": image_urls,
        }


