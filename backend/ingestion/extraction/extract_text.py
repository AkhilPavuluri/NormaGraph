"""
PDF text extraction for ingestion_v2.

Clean, multi-strategy extraction without over-engineering.
Uses: pdfplumber (primary) → PyPDF2 (fallback) → OCR (if needed)
"""
from pathlib import Path
from typing import Dict, Optional, List
import logging

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

logger = logging.getLogger(__name__)


class TextExtractor:
    """Extract text from PDFs using multiple strategies."""
    
    def __init__(self, use_pdfplumber: bool = True, fallback_to_pypdf: bool = True):
        """
        Initialize text extractor.
        
        Args:
            use_pdfplumber: Use pdfplumber as primary method
            fallback_to_pypdf: Fall back to PyPDF2 if pdfplumber fails
        """
        self.use_pdfplumber = use_pdfplumber and PDFPLUMBER_AVAILABLE
        self.fallback_to_pypdf = fallback_to_pypdf and PYPDF2_AVAILABLE
        
        if not self.use_pdfplumber and not PDFPLUMBER_AVAILABLE:
            logger.warning("pdfplumber not available")
        
        if not self.fallback_to_pypdf and not PYPDF2_AVAILABLE:
            logger.warning("PyPDF2 not available")
    
    def extract(self, pdf_path: Path) -> Dict:
        """
        Extract text from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with:
                - text: Extracted text
                - method: Extraction method used
                - page_count: Number of pages
                - word_count: Number of words
                - success: Boolean
        """
        logger.info(f"Extracting text from: {pdf_path.name}")
        
        # Try pdfplumber first
        if self.use_pdfplumber:
            result = self._extract_with_pdfplumber(pdf_path)
            if result["success"] and result["word_count"] > 50:
                logger.info(f"✓ Extracted with pdfplumber: {result['word_count']} words")
                return result
            logger.debug("pdfplumber extraction insufficient")
        
        # Fallback to PyPDF2
        if self.fallback_to_pypdf:
            result = self._extract_with_pypdf(pdf_path)
            if result["success"] and result["word_count"] > 50:
                logger.info(f"✓ Extracted with PyPDF2: {result['word_count']} words")
                return result
            logger.debug("PyPDF2 extraction insufficient")
        
        # If both failed, return empty result
        logger.warning(f"All extraction methods failed for {pdf_path.name}")
        return {
            "text": "",
            "method": "none",
            "page_count": 0,
            "word_count": 0,
            "char_count": 0,
            "success": False,
            "needs_ocr": True,
            "tables": [],
            "table_count": 0
        }
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> Dict:
        """Extract text, tables, and coordinates using pdfplumber."""
        try:
            text_parts = []
            extracted_tables = []
            word_coords = []
            page_count = 0
            
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        # Extract regular text
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                        
                        # Extract word coordinates for visual anchoring
                        words = page.extract_words(
                            x_tolerance=3, 
                            y_tolerance=3, 
                            keep_blank_chars=False, 
                            use_text_flow=True
                        )
                        for word in words:
                            word_coords.append({
                                "text": word["text"],
                                "page": page_num,
                                "bbox": [word["x0"], word["top"], word["x1"], word["bottom"]],
                                "upright": word.get("upright", True)
                            })
                        
                        # Extract tables from this page
                        page_tables = self._extract_tables_from_page(page, page_num)
                        extracted_tables.extend(page_tables)
                        
                    except Exception as e:
                        logger.debug(f"Error extracting page {page_num}: {e}")
                        continue
            
            # Combine regular text and table text
            all_text = "\n\n".join(text_parts)
            
            # Add table text to main text if tables were found
            if extracted_tables:
                table_texts = []
                for table_info in extracted_tables:
                    table_texts.append(table_info['formatted_text'])
                
                # Merge table text with regular text
                if table_texts:
                    all_text += "\n\n" + "\n\n".join(table_texts)
            
            word_count = len(all_text.split())
            
            return {
                "text": all_text,
                "method": "pdfplumber",
                "page_count": page_count,
                "word_count": word_count,
                "char_count": len(all_text),
                "success": word_count > 0,
                "needs_ocr": word_count < 50,
                "tables": extracted_tables,
                "table_count": len(extracted_tables),
                "word_coords": word_coords
            }
            
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return {
                "text": "",
                "method": "pdfplumber",
                "success": False,
                "error": str(e),
                "tables": [],
                "table_count": 0
            }
    
    def _extract_tables_from_page(self, page, page_num: int) -> List[Dict]:
        """Extract tables from a single page"""
        tables = []
        
        try:
            # Extract tables using pdfplumber
            page_tables = page.extract_tables()
            
            for table_num, table in enumerate(page_tables):
                if not table or len(table) == 0:
                    continue
                
                # Convert table to text format
                table_text_rows = []
                headers = []
                
                for row_idx, row in enumerate(table):
                    if not row:
                        continue
                    
                    # Clean and format cells
                    clean_row = []
                    for cell in row:
                        if cell is None:
                            clean_row.append("")
                        else:
                            # Clean cell text
                            clean_cell = str(cell).strip().replace('\n', ' ')
                            clean_row.append(clean_cell)
                    
                    # Skip empty rows
                    if all(cell == "" or cell is None for cell in clean_row):
                        continue
                    
                    # First non-empty row might be headers
                    if row_idx == 0 or (not headers and len(clean_row) > 1):
                        headers = clean_row[:]
                    
                    # Convert to text format
                    row_text = " | ".join(clean_row)
                    table_text_rows.append(row_text)
                
                if table_text_rows:
                    # Create formatted table text
                    formatted_table = "\n".join(table_text_rows)
                    
                    tables.append({
                        'page_num': page_num,
                        'table_num': table_num,
                        'raw_data': table,
                        'headers': headers,
                        'text_rows': table_text_rows,
                        'formatted_text': formatted_table,
                        'row_count': len(table_text_rows),
                        'col_count': len(headers) if headers else 0
                    })
        
        except Exception as e:
            logger.debug(f"Error extracting tables from page {page_num}: {e}")
        
        return tables
    
    def _extract_with_pypdf(self, pdf_path: Path) -> Dict:
        """Extract text using PyPDF2."""
        try:
            text_parts = []
            page_count = 0
            
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                page_count = len(pdf_reader.pages)
                
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as e:
                        logger.debug(f"Error extracting page: {e}")
                        continue
            
            text = "\n\n".join(text_parts)
            word_count = len(text.split())
            
            return {
                "text": text,
                "method": "pypdf2",
                "page_count": page_count,
                "word_count": word_count,
                "char_count": len(text),
                "success": word_count > 0,
                "needs_ocr": word_count < 50,
                "tables": [],
                "table_count": 0
            }
            
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return {
                "text": "",
                "method": "pypdf2",
                "success": False,
                "error": str(e),
                "tables": [],
                "table_count": 0
            }


def extract_text(pdf_path: Path) -> Dict:
    """
    Convenience function for text extraction.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extraction result dictionary
    """
    extractor = TextExtractor()
    return extractor.extract(pdf_path)