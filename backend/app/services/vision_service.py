import os
import base64
import logging
from typing import Optional, Dict
from langchain_core.messages import HumanMessage
from app.services.llm_utils import get_llm

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self, model_choice: str = "gemini-2.5-flash"):
        self.model_choice = model_choice
        try:
            self.llm = get_llm(model_choice)
        except Exception as e:
            logger.error(f"VisionService failed to initialize LLM: {e}")
            self.llm = None

    async def analyze_screenshot(self, image_path: str, query: str = "") -> Dict:
        """
        Analyze a screenshot using Vision-AI to extract text and identify visual threats.
        """
        if not self.llm or not os.path.exists(image_path):
            return {"error": "LLM not initialized or image not found", "ocr_text": ""}

        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            prompt = f"""
            Analyze this dark web screenshot.
            1. Extract ALL visible text (OCR).
            2. Identify any sensitive information (bank accounts, crypto wallets, emails, PGP keys).
            3. Provide a brief 1-sentence summary of what this site appears to be.
            4. If the user query "{query}" is related to anything in the image, explain the connection.
            
            Output format:
            Summary: [text]
            OCR: [all text found]
            Entities: [list of emails/wallets/etc]
            """

            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"},
                    },
                ]
            )

            # Gemini-2.5-Flash supports multimodal input via LangChain
            response = await self.llm.ainvoke([message])
            content = response.content

            # Simple parsing
            summary = ""
            ocr_text = ""
            entities = []

            if "Summary:" in content:
                summary = content.split("Summary:")[1].split("OCR:")[0].strip()
            if "OCR:" in content:
                ocr_text = content.split("OCR:")[1].split("Entities:")[0].strip()
            if "Entities:" in content:
                entities_raw = content.split("Entities:")[1].strip()
                entities = [e.strip() for e in entities_raw.split("\n") if e.strip()]

            return {
                "success": True,
                "visual_summary": summary,
                "ocr_text": ocr_text,
                "visual_entities": entities,
                "raw_analysis": content
            }

        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {"error": str(e), "ocr_text": ""}

vision_service = VisionService()
