"""
Image Parser Agent using LangChain + Groq (with OCR support)
Loads images from GCS (or preprocessed URLs), optionally preprocesses + OCR,
then runs LLM with multimodal image+text input.
"""

from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from PIL import Image, ImageOps, ImageFilter
import io
import httpx
import os
import logging

from config.settings import get_settings
from services.gcs_service import gcs_service

# Try to import pytesseract, but make it optional
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available. OCR features will be disabled.")

logger = logging.getLogger(__name__)


def _preprocess_image_bytes(image_bytes: bytes) -> bytes:
    """Preprocess image: grayscale, sharpen, and resize if needed."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Convert to grayscale for better OCR and smaller file size
        img = ImageOps.grayscale(img)
        # Sharpen for better text recognition
        img = img.filter(ImageFilter.SHARPEN)
        
        # Resize if too large (max width 1600px)
        max_w = 1600
        if img.width > max_w:
            ratio = max_w / float(img.width)
            new_h = int(img.height * ratio)
            img = img.resize((max_w, new_h), Image.Resampling.LANCZOS)
        
        # Save as JPEG with compression
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=60, optimize=True)
        return out.getvalue()
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {str(e)}, using original")
        return image_bytes


def _extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """Run OCR to extract visible text from image."""
    if not TESSERACT_AVAILABLE:
        return ""
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.grayscale(img)
        img = img.filter(ImageFilter.SHARPEN)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        logger.debug(f"OCR extraction failed: {str(e)}")
        return ""


class ImageParserAgent:
    def __init__(self):
        self.settings = get_settings()
        # Use multimodal Groq model - ensure we use the configured model
        model_name = self.settings.GROQ_IMAGE_MODEL or "llama-3.2-11b-vision-preview"
        self.llm = ChatGroq(
            api_key=self.settings.GROQ_API_KEY,
            model=model_name,
            temperature=0.1,
        )
        logger.info(f"Initialized ImageParserAgent with model: {model_name}")
        
        # Prompt template for image analysis
        self.prompt_template = (
            "You analyze images for learning. Given image URLs and any extracted text (OCR), "
            "identify key visual learning cues. Return ONLY valid JSON with:\n"
            "  objects (list of objects you identify in the image),\n"
            "  text_snippets (list of text strings from OCR),\n"
            "  diagrams (list of diagram descriptions),\n"
            "  concepts (list of educational concepts),\n"
            "  description (string summarizing the image).\n\n"
            "Image URLs: {signed_urls}\n\n"
            "Extracted OCR text: {extracted_texts}\n\n"
            "Return JSON only, no markdown, no code blocks."
        )

    async def parse(self, user_id: str, image_paths_or_urls: List[str]) -> Dict[str, Any]:
        """Parse images and extract learning content using vision model and OCR."""
        if not image_paths_or_urls:
            logger.warning("No image paths provided to ImageParserAgent.parse")
            return {
                "type": "image",
                "urls": [],
                "ocr_texts": [],
                "raw": "",
            }
        
        signed_urls: List[str] = []
        extracted_texts: List[str] = []

        logger.info(f"Processing {len(image_paths_or_urls)} image(s) for user {user_id}")

        # Process items: either URL or GCS path
        for idx, item in enumerate(image_paths_or_urls):
            try:
                if item.startswith("http"):
                    # Already a signed URL, use directly
                    signed_urls.append(item)
                    # Optionally fetch and OCR for additional text extraction
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(item, timeout=60.0)
                            resp.raise_for_status()
                            ocr = _extract_text_from_image_bytes(resp.content)
                            if ocr:
                                extracted_texts.append(ocr)
                                logger.debug(f"Extracted OCR text from image {idx + 1}: {len(ocr)} chars")
                    except Exception as e:
                        logger.debug(f"OCR extraction failed for image {idx + 1}: {str(e)}")
                else:
                    # GCS path - need to create signed URL and optionally preprocess
                    try:
                        url = gcs_service.create_signed_download_url(item)
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(url, timeout=60.0)
                            resp.raise_for_status()
                            
                            # Preprocess image for better quality
                            pre = _preprocess_image_bytes(resp.content)
                            
                            # Extract OCR text from preprocessed image
                            ocr = _extract_text_from_image_bytes(pre)
                            if ocr:
                                extracted_texts.append(ocr)
                                logger.debug(f"Extracted OCR text from image {idx + 1}: {len(ocr)} chars")

                            # Upload preprocessed image and get signed URL
                            base = os.path.basename(item)
                            # Ensure proper file extension
                            if not base.lower().endswith(('.jpg', '.jpeg', '.png')):
                                base = f"{base}.jpg"
                            processed_path = f"users/{user_id}/processed/images/{base}"
                            gcs_service.upload_file_directly(processed_path, pre, "image/jpeg")
                            signed_url = gcs_service.create_signed_download_url(processed_path)
                            signed_urls.append(signed_url)
                            logger.debug(f"Processed and uploaded image {idx + 1} to {processed_path}")
                    except Exception as e:
                        logger.warning(f"Failed to process image {idx + 1} ({item}): {str(e)}")
                        # Fallback to original URL
                        try:
                            signed_urls.append(gcs_service.create_signed_download_url(item))
                        except Exception as fallback_error:
                            logger.error(f"Fallback URL creation also failed for {item}: {str(fallback_error)}")
            except Exception as e:
                logger.error(f"Unexpected error processing image {idx + 1}: {str(e)}")
                continue

        if not signed_urls:
            logger.warning("No valid image URLs after processing")
            return {
                "type": "image",
                "urls": [],
                "ocr_texts": extracted_texts,
                "raw": "",
            }

        # Prepare LLM input - format URLs and OCR text for the prompt
        urls_str = "\n".join([f"- {url}" for url in signed_urls])
        ocr_str = "\n\n".join([f"Image {i+1} OCR:\n{text}" for i, text in enumerate(extracted_texts)]) if extracted_texts else "None"
        
        prompt_text = self.prompt_template.format(
            signed_urls=urls_str,
            extracted_texts=ocr_str
        )

        # For Groq vision models, we need to pass images in a specific format
        # Create messages with image URLs
        try:
            # Try using HumanMessage with image content for vision models
            messages = [
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt_text},
                        *[{"type": "image_url", "image_url": {"url": url}} for url in signed_urls]
                    ]
                )
            ]
            
            response = await self.llm.ainvoke(messages)
            raw_content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"Successfully processed {len(signed_urls)} image(s), response length: {len(raw_content)}")
        except Exception as e:
            logger.error(f"LLM invocation failed: {str(e)}")
            # Fallback: try simple text prompt with URLs as strings
            try:
                response = await self.llm.ainvoke(prompt_text)
                raw_content = response.content if hasattr(response, 'content') else str(response)
            except Exception as fallback_error:
                logger.error(f"Fallback LLM invocation also failed: {str(fallback_error)}")
                raw_content = f"Error processing images: {str(e)}"

        return {
            "type": "image",
            "urls": signed_urls,
            "ocr_texts": extracted_texts,
            "raw": raw_content,
        }
