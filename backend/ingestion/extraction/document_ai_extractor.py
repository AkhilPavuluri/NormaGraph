"""
Google Document AI Integration for Layout-Aware Extraction

Provides structured extraction from PDFs using Document AI,
especially useful for judicial documents with complex layouts.
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from google.cloud import documentai
from google.api_core import exceptions

logger = logging.getLogger(__name__)


class DocumentAIExtractor:
    """
    Extracts text and structure from PDFs using Google Document AI.
    
    Provides:
    - Layout analysis (headers, paragraphs, tables, lists)
    - Entity extraction (dates, names, citations)
    - Table extraction with structure
    - Better handling of multi-column layouts
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us",
        processor_id: Optional[str] = None
    ):
        """
        Initialize Document AI client.
        
        Args:
            project_id: GCP Project ID
            location: Processor location (us, eu, asia)
            processor_id: Document AI processor ID (optional, uses default if not provided)
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self.processor_id = processor_id or os.getenv("DOCUMENT_AI_PROCESSOR_ID")
        
        if not self.project_id:
            logger.warning("Document AI: Project ID not found - will use fallback extraction")
            self.available = False
            return
        
        try:
            # Initialize Document AI client
            self.client = documentai.DocumentProcessorServiceClient()
            
            # Build processor name
            if self.processor_id:
                self.processor_name = self.client.processor_path(
                    self.project_id, self.location, self.processor_id
                )
            else:
                # Use default form parser
                self.processor_name = self.client.processor_path(
                    self.project_id, self.location, "default-processor"
                )
            
            self.available = True
            logger.info(f"✅ Document AI initialized (processor: {self.processor_name})")
            
        except Exception as e:
            logger.warning(f"⚠️ Document AI initialization failed: {e}")
            self.available = False
            self.client = None
    
    def extract(
        self,
        pdf_path: Path,
        use_layout: bool = True,
        extract_tables: bool = True,
        extract_entities: bool = True
    ) -> Dict:
        """
        Extract text and structure from PDF using Document AI.
        
        Args:
            pdf_path: Path to PDF file
            use_layout: Extract layout information (headers, paragraphs)
            extract_tables: Extract tables with structure
            extract_entities: Extract entities (dates, names, etc.)
            
        Returns:
            Dictionary with:
                - text: Full extracted text
                - layout: List of layout elements (if use_layout=True)
                - tables: List of extracted tables (if extract_tables=True)
                - entities: List of extracted entities (if extract_entities=True)
                - method: "document_ai"
                - success: Boolean
        """
        if not self.available:
            return {
                "text": "",
                "layout": [],
                "tables": [],
                "entities": [],
                "method": "document_ai",
                "success": False,
                "error": "Document AI not available"
            }
        
        try:
            logger.info(f"Extracting with Document AI: {pdf_path.name}")
            
            # Read PDF file
            with open(pdf_path, "rb") as f:
                pdf_content = f.read()
            
            # Create request
            raw_document = documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            )
            
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )
            
            # Process document
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract text
            text = document.text
            
            # Extract layout if requested
            layout = []
            if use_layout:
                layout = self._extract_layout(document)
            
            # Extract tables if requested
            tables = []
            if extract_tables:
                tables = self._extract_tables(document)
            
            # Extract entities if requested
            entities = []
            if extract_entities:
                entities = self._extract_entities(document)
            
            logger.info(f"✅ Document AI extraction complete: {len(text)} chars, "
                       f"{len(layout)} layout elements, {len(tables)} tables, {len(entities)} entities")
            
            return {
                "text": text,
                "layout": layout,
                "tables": tables,
                "entities": entities,
                "method": "document_ai",
                "success": True,
                "page_count": len(document.pages),
                "word_count": len(text.split()),
                "char_count": len(text)
            }
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"Document AI API error: {e}")
            return {
                "text": "",
                "layout": [],
                "tables": [],
                "entities": [],
                "method": "document_ai",
                "success": False,
                "error": f"API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Document AI extraction failed: {e}")
            return {
                "text": "",
                "layout": [],
                "tables": [],
                "entities": [],
                "method": "document_ai",
                "success": False,
                "error": str(e)
            }
    
    def _extract_layout(self, document) -> List[Dict]:
        """Extract layout elements (headers, paragraphs, lists)"""
        layout = []
        
        for page in document.pages:
            for block in page.blocks:
                block_text = self._get_text_from_layout_element(document, block.layout)
                
                layout.append({
                    "type": "block",
                    "text": block_text,
                    "confidence": block.layout.confidence if hasattr(block.layout, 'confidence') else 1.0,
                    "page": page.page_number if hasattr(page, 'page_number') else 0
                })
        
        return layout
    
    def _extract_tables(self, document) -> List[Dict]:
        """Extract tables with structure"""
        tables = []
        
        for page in document.pages:
            for table in page.tables:
                table_data = self._extract_table_structure(document, table)
                tables.append({
                    "rows": table_data["rows"],
                    "columns": table_data["columns"],
                    "data": table_data["data"],
                    "page": page.page_number if hasattr(page, 'page_number') else 0
                })
        
        return tables
    
    def _extract_entities(self, document) -> List[Dict]:
        """Extract entities (dates, names, citations, etc.)"""
        entities = []
        
        if hasattr(document, 'entities') and document.entities:
            for entity in document.entities:
                entities.append({
                    "type": entity.type_ if hasattr(entity, 'type_') else "unknown",
                    "text": entity.mention_text if hasattr(entity, 'mention_text') else "",
                    "confidence": entity.confidence if hasattr(entity, 'confidence') else 1.0
                })
        
        return entities
    
    def _get_text_from_layout_element(self, document, layout_element) -> str:
        """Extract text from a layout element"""
        text_segments = []
        
        if hasattr(layout_element, 'text_anchor') and layout_element.text_anchor:
            for segment in layout_element.text_anchor.text_segments:
                start_index = segment.start_index if hasattr(segment, 'start_index') else 0
                end_index = segment.end_index if hasattr(segment, 'end_index') else 0
                text_segments.append(document.text[start_index:end_index])
        
        return " ".join(text_segments)
    
    def _extract_table_structure(self, document, table) -> Dict:
        """Extract structured table data"""
        rows = []
        columns = []
        data = []
        
        if hasattr(table, 'header_rows') and table.header_rows:
            for header_row in table.header_rows:
                row_data = []
                for cell in header_row.cells:
                    cell_text = self._get_text_from_layout_element(document, cell.layout)
                    row_data.append(cell_text)
                    if cell_text not in columns:
                        columns.append(cell_text)
                rows.append(row_data)
        
        if hasattr(table, 'body_rows') and table.body_rows:
            for body_row in table.body_rows:
                row_data = []
                for cell in body_row.cells:
                    cell_text = self._get_text_from_layout_element(document, cell.layout)
                    row_data.append(cell_text)
                data.append(row_data)
        
        return {
            "rows": rows,
            "columns": columns,
            "data": data
        }


def extract_with_document_ai(
    pdf_path: Path,
    project_id: Optional[str] = None,
    fallback_to_standard: bool = True
) -> Dict:
    """
    Convenience function to extract with Document AI, with fallback.
    
    Args:
        pdf_path: Path to PDF
        project_id: GCP Project ID
        fallback_to_standard: Fall back to standard extraction if Document AI fails
        
    Returns:
        Extraction result dictionary
    """
    extractor = DocumentAIExtractor(project_id=project_id)
    
    if not extractor.available:
        if fallback_to_standard:
            logger.info("Document AI not available, falling back to standard extraction")
            from ingestion.extraction.extract_text import TextExtractor
            standard_extractor = TextExtractor()
            return standard_extractor.extract(pdf_path)
        else:
            return {
                "text": "",
                "success": False,
                "error": "Document AI not available and fallback disabled"
            }
    
    result = extractor.extract(pdf_path)
    
    if not result["success"] and fallback_to_standard:
        logger.warning("Document AI extraction failed, falling back to standard extraction")
        from ingestion.extraction.extract_text import TextExtractor
        standard_extractor = TextExtractor()
        return standard_extractor.extract(pdf_path)
    
    return result

