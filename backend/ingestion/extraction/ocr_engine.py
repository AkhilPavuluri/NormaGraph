"""
Selective OCR engine for low-quality PDFs.

Simple, targeted OCR - only used when regular extraction fails.
"""
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


class OCREngine:
    """Simple OCR engine for problematic PDFs."""
    
    def __init__(self, confidence_threshold: float = 0.3):
        """
        Initialize OCR engine.
        
        Args:
            confidence_threshold: Minimum confidence for OCR (0-1)
        """
        self.confidence_threshold = confidence_threshold
        self.available = TESSERACT_AVAILABLE
        
        if not self.available:
            logger.warning("Tesseract OCR not available. Install: apt-get install tesseract-ocr pytesseract pdf2image")
    
    def needs_ocr(self, text: str, page_count: int) -> bool:
        """
        Check if document needs OCR.
        
        Args:
            text: Extracted text
            page_count: Number of pages
            
        Returns:
            True if OCR is needed
        """
        if not text or len(text.strip()) == 0:
            return True
        
        word_count = len(text.split())
        words_per_page = word_count / max(page_count, 1)
        
        # If less than 10 words per page, probably needs OCR
        return words_per_page < 10
    
    def ocr_pdf(self, pdf_path: Path, max_pages: Optional[int] = None) -> Dict:
        """
        Perform OCR on PDF.
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to OCR (None for all)
            
        Returns:
            OCR result dictionary
        """
        if not self.available:
            return {
                "text": "",
                "success": False,
                "error": "Tesseract OCR not available",
            }
        
        try:
            logger.info(f"Running OCR on: {pdf_path.name}")
            
            # Convert PDF to images
            images = pdf2image.convert_from_path(str(pdf_path))
            
            if max_pages:
                images = images[:max_pages]
            
            # OCR each page
            text_parts = []
            for i, image in enumerate(images):
                try:
                    page_text = pytesseract.image_to_string(image, lang='eng')
                    if page_text.strip():
                        text_parts.append(page_text)
                    logger.debug(f"OCR page {i+1}/{len(images)}")
                except Exception as e:
                    logger.warning(f"OCR failed for page {i+1}: {e}")
                    continue
            
            text = "\n\n".join(text_parts)
            word_count = len(text.split())
            
            logger.info(f"✓ OCR completed: {word_count} words from {len(images)} pages")
            
            return {
                "text": text,
                "method": "ocr",
                "page_count": len(images),
                "word_count": word_count,
                "char_count": len(text),
                "success": word_count > 0,
            }
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return {
                "text": "",
                "method": "ocr",
                "success": False,
                "error": str(e),
            }
    
    def selective_ocr(self, pdf_path: Path, existing_text: str, page_count: int) -> str:
        """
        Perform selective OCR only if needed.
        
        Args:
            pdf_path: Path to PDF
            existing_text: Already extracted text
            page_count: Number of pages
            
        Returns:
            Combined text (existing + OCR if needed)
        """
        if not self.needs_ocr(existing_text, page_count):
            logger.debug("OCR not needed - extraction is sufficient")
            return existing_text
        
        logger.info("Running selective OCR...")
        ocr_result = self.ocr_pdf(pdf_path)
        
        if ocr_result["success"] and ocr_result["word_count"] > len(existing_text.split()):
            logger.info(f"OCR improved extraction: {ocr_result['word_count']} words")
            return ocr_result["text"]
        else:
            logger.info("OCR did not improve extraction, keeping original")
            return existing_text


def ocr_if_needed(pdf_path: Path, existing_text: str, page_count: int) -> str:
    """
    Convenience function for selective OCR.
    
    Args:
        pdf_path: Path to PDF
        existing_text: Already extracted text
        page_count: Number of pages
        
    Returns:
        Final text (with OCR if needed)
    """
    engine = OCREngine()
    return engine.selective_ocr(pdf_path, existing_text, page_count)