"""
Main pipeline orchestrator for ingestion_v2.

COMPLETE pipeline flow:
1. Extract text from PDF
2. Clean and normalize
3. Classify vertical
4. Parse structure (vertical-aware)
5. Chunk document (vertical-aware)
6. Extract entities (regex + optional LLM)
7. Extract relations (regex + LLM for important docs)
8. Build metadata (clean, retrieval-optimized)
9. Write outputs (organized by vertical)
"""
from pathlib import Path
from typing import Dict, List, Optional
import logging
import sys
import time

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ingestion.config.settings import (
    OUTPUT_DIR, VERTICALS, 
    USE_LLM_FOR_ENTITIES, USE_LLM_FOR_RELATIONS,
    LLM_ENABLED_VERTICALS, RELATION_ENABLED_VERTICALS,
    validate_config
)

from backend.ingestion.io.file_loader import FileLoader
from backend.ingestion.io.json_writer import write_json, write_jsonl
from backend.ingestion.io.text_writer import write_text
from backend.ingestion.io.directory_manager import DirectoryManager

from backend.ingestion.extraction.extract_text import TextExtractor
from backend.ingestion.extraction.ocr_engine import OCREngine
from backend.ingestion.extraction.document_ai_extractor import DocumentAIExtractor
from backend.ingestion.extraction.extract_metadata_basic import extract_basic_metadata

from backend.ingestion.cleaning.text_cleaner import TextCleaner
from backend.ingestion.cleaning.normalization_rules import NormalizationRules

from backend.ingestion.classification.vertical_classifier import VerticalClassifier
from backend.ingestion.classification.document_classifier import DocumentClassifier

# Structure parsers
from backend.ingestion.structure.go_structure import GOStructureParser
from backend.ingestion.structure.legal_structure import LegalStructureParser
from backend.ingestion.structure.judicial_structure import JudicialStructureParser
from backend.ingestion.structure.data_structure import DataStructureParser
from backend.ingestion.structure.scheme_structure import SchemeStructureParser

# Chunking
from backend.ingestion.chunking.chunk_go import GOChunker
from backend.ingestion.chunking.chunk_legal import LegalChunker
from backend.ingestion.chunking.chunk_judicial import JudicialChunker
from backend.ingestion.chunking.chunk_data import DataChunker
from backend.ingestion.chunking.chunk_scheme import SchemeChunker

# Entities
from backend.ingestion.entities.entity_extractor import EntityExtractor
from backend.ingestion.entities.domain_extractor import DomainExtractor

# Relations
from backend.ingestion.relations.relation_extractor import RelationExtractor
from backend.ingestion.relations.relation_rules import should_extract_relations, AUTHORITY_WEIGHTS
from backend.ingestion.relations.legal_status_resolver import LegalStatusResolver

# Metadata
from backend.ingestion.metadata.metadata_builder import MetadataBuilder
from backend.ingestion.utils.logging_config import setup_logging, StageLogger

logger = logging.getLogger(__name__)


def _make_json_serializable(obj):
    """Convert dataclass objects and other non-serializable types to dicts."""
    if hasattr(obj, '__dict__'):
        # It's a dataclass or object
        if hasattr(obj, '__dataclass_fields__'):
            # Dataclass
            return {field: _make_json_serializable(getattr(obj, field)) 
                   for field in obj.__dataclass_fields__}
        else:
            # Regular object
            return {k: _make_json_serializable(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    else:
        return obj


class IngestionPipeline:
    """
    COMPLETE ingestion pipeline - uses all components properly.
    
    No over-engineering. No BS. Just works.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize pipeline with ALL components.
        
        Args:
            output_dir: Output directory (defaults to config)
        """
        # Validate settings
        errors = validate_config()
        if errors:
            logger.warning(f"Config warnings: {errors}")
        
        # Initialize I/O components
        self.output_dir = output_dir or OUTPUT_DIR
        
        # Use GCS file loader if available, fallback to local
        try:
            from backend.ingestion.io.gcs_file_loader import GCSFileLoader
            self.file_loader = GCSFileLoader()
            logger.info("✅ Using GCS file loader (cloud-based)")
        except (ImportError, ValueError) as e:
            logger.warning(f"⚠️ GCS file loader not available: {e}. Falling back to local file loader.")
            from backend.ingestion.io.file_loader import FileLoader
            self.file_loader = FileLoader()
        
        self.dir_manager = DirectoryManager(self.output_dir)
        
        # Initialize extraction components
        self.text_extractor = TextExtractor()
        self.ocr_engine = OCREngine()
        
        # Initialize Document AI extractor (for judicial documents with complex layouts)
        try:
            self.document_ai_extractor = DocumentAIExtractor()
            if self.document_ai_extractor.available:
                logger.info("✅ Document AI extractor initialized (will be used for judicial documents)")
            else:
                logger.info("⚠️ Document AI not available - will use standard extraction")
                self.document_ai_extractor = None
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize Document AI: {e} - will use standard extraction")
            self.document_ai_extractor = None
        
        # Initialize cleaning components
        self.text_cleaner = TextCleaner()
        self.normalizer = NormalizationRules()
        
        # Initialize classification
        # Initialize classification
        self.vertical_classifier = VerticalClassifier()
        self.doc_classifier = DocumentClassifier(use_llm=False)
        
        # Initialize structure parsers
        self.structure_parsers = {
            "go": GOStructureParser(),
            "legal": LegalStructureParser(),
            "judicial": JudicialStructureParser(),
            "data": DataStructureParser(),
            "scheme": SchemeStructureParser()
        }
        
        # Initialize chunkers
        self.chunkers = {
            "go": GOChunker(),
            "legal": LegalChunker(),
            "judicial": JudicialChunker(),
            "data": DataChunker(),
            "scheme": SchemeChunker()
        }
        
        # Initialize entity extractor
        self.entity_extractor = EntityExtractor(
            use_llm=USE_LLM_FOR_ENTITIES,
            llm_enabled_verticals=LLM_ENABLED_VERTICALS
        )
        
        # Initialize relation extractor
        self.relation_extractor = RelationExtractor(
            use_llm=USE_LLM_FOR_RELATIONS
        )
        
        # Initialize metadata builder
        self.metadata_builder = MetadataBuilder()
        self.domain_extractor = DomainExtractor()
        
        # Initialize GO chain builder for lineage tracking
        from backend.ingestion.entities.go_chain_builder import GOChainBuilder
        self.go_chain_builder = GOChainBuilder()
        self.legal_resolver = LegalStatusResolver(AUTHORITY_WEIGHTS)
        
        # Create vertical directories
        self.dir_manager.create_vertical_dirs(VERTICALS)
        
        logger.info("✅ Complete ingestion pipeline initialized")
        logger.info(f"   - LLM entities: {USE_LLM_FOR_ENTITIES}")
        logger.info(f"   - LLM relations: {USE_LLM_FOR_RELATIONS}")
    
    def process_document(self, file_path: Path) -> Dict:
        """
        Process a single document through the COMPLETE pipeline.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Processing result dictionary
        """
        start_time = time.time()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📄 PROCESSING DOCUMENT: {file_path.name}")
        logger.info(f"{'='*80}")
        logger.info(f"File path: {file_path}")
        logger.info(f"File size: {file_path.stat().st_size / (1024*1024):.2f} MB")
        
        try:
            # Generate doc_id
            doc_id = file_path.stem.lower().replace(' ', '_').replace('-', '_')
            logger.info(f"Document ID: {doc_id}")
            
            # ================================================================
            # STAGE 1: TEXT EXTRACTION
            # ================================================================
            with StageLogger(logger, "STAGE 1: TEXT EXTRACTION") as stage:
                stage.step("Loading PDF file")
                
                # Try Document AI first if available (especially useful for judicial documents)
                extraction_result = None
                if self.document_ai_extractor and self.document_ai_extractor.available:
                    stage.step("Attempting Document AI extraction (layout-aware)")
                    doc_ai_result = self.document_ai_extractor.extract(
                        file_path,
                        use_layout=True,
                        extract_tables=True,
                        extract_entities=True
                    )
                    
                    if doc_ai_result["success"] and doc_ai_result.get("word_count", 0) > 50:
                        extraction_result = doc_ai_result
                        extraction_result["method"] = "document_ai"
                        stage.metric("Extraction method", "Document AI")
                        logger.info("✅ Using Document AI extraction (layout-aware)")
                    else:
                        stage.step("Document AI extraction insufficient, falling back to standard")
                        logger.info("⚠️ Document AI extraction insufficient, using standard extraction")
                
                # Fall back to standard extraction if Document AI not used or failed
                if extraction_result is None:
                    extraction_result = self.text_extractor.extract(file_path)
                    stage.metric("Extraction method", extraction_result.get("method", "standard"))
                
                # Check if we should try OCR before failing
                if not extraction_result["success"] and not extraction_result.get("needs_ocr", False):
                    stage.error(f"Text extraction failed: {extraction_result.get('error', 'Unknown error')}")
                    return {"status": "failed", "stage": "extraction", "doc_id": doc_id}
                
                text = extraction_result["text"]
                page_count = extraction_result.get("page_count", 0)
                word_count = extraction_result.get("word_count", 0)
                char_count = extraction_result.get("char_count", len(text))
                method = extraction_result.get("method", "unknown")
                word_coords = extraction_result.get("word_coords", [])  # New: Capture word coords
                
                stage.metric("Pages extracted", page_count)
                stage.metric("Words extracted", word_count)
                stage.metric("Characters extracted", char_count)
                stage.metric("Word coords captured", len(word_coords))
                
                # Log table extraction metrics (from Document AI or standard extraction)
                extracted_tables = extraction_result.get("tables", [])
                if extracted_tables:
                    stage.metric("Tables extracted", len(extracted_tables))
                    table_rows = sum(table.get('row_count', 0) for table in extracted_tables)
                    if table_rows > 0:
                        stage.metric("Total table rows", table_rows)
                
                # Log layout info if from Document AI
                if method == "document_ai":
                    layout_elements = extraction_result.get("layout", [])
                    entities = extraction_result.get("entities", [])
                    if layout_elements:
                        stage.metric("Layout elements", len(layout_elements))
                    if entities:
                        stage.metric("Entities extracted", len(entities))
                
                # OCR if needed (including complete extraction failures)
                if extraction_result.get("needs_ocr", False):
                    if not extraction_result["success"]:
                        stage.step("Text extraction failed - attempting OCR")
                        stage.warning(f"Standard extraction failed, trying OCR on {page_count} pages")
                        ocr_result = self.ocr_engine.ocr_pdf(file_path)
                        if ocr_result["success"]:
                            text = ocr_result["text"]
                            word_count = ocr_result["word_count"]
                            char_count = ocr_result["char_count"]
                            stage.metric("Words from OCR", word_count)
                        else:
                            stage.error(f"OCR also failed: {ocr_result.get('error', 'Unknown error')}")
                            return {"status": "failed", "stage": "extraction", "doc_id": doc_id}
                    else:
                        stage.step("Low quality text detected - running OCR")
                        stage.warning(f"Text quality low ({word_count} words for {page_count} pages)")
                        text = self.ocr_engine.selective_ocr(file_path, text, page_count)
                        word_count = len(text.split())
                        char_count = len(text)
                        stage.metric("Words after OCR", word_count)
                        stage.metric("Characters after OCR", char_count)
                
                stage.success(f"Text extraction complete: {word_count} words, {page_count} pages")
            
            # ================================================================
            # STAGE 2: TEXT CLEANING
            # ================================================================
            with StageLogger(logger, "STAGE 2: TEXT CLEANING & NORMALIZATION") as stage:
                stage.step("Normalizing Unicode characters")
                cleaned_text = self.text_cleaner.clean(text)
                
                stage.step("Applying normalization rules")
                cleaned_text = self.normalizer.apply_all(cleaned_text)
                
                original_words = word_count
                cleaned_words = len(cleaned_text.split())
                original_chars = len(text)
                cleaned_chars = len(cleaned_text)
                
                stage.metric("Original words", original_words)
                stage.metric("Cleaned words", cleaned_words)
                stage.metric("Word reduction", f"{((original_words - cleaned_words) / max(original_words, 1) * 100):.1f}%")
                stage.metric("Original characters", original_chars)
                stage.metric("Cleaned characters", cleaned_chars)
                stage.metric("Character reduction", f"{((original_chars - cleaned_chars) / max(original_chars, 1) * 100):.1f}%")
                
                stage.success(f"Text cleaning complete: {cleaned_words} words, {cleaned_chars} characters")
            
            # ================================================================
            # STAGE 3: CLASSIFICATION
            # ================================================================
            with StageLogger(logger, "STAGE 3: DOCUMENT CLASSIFICATION") as stage:
                # Vertical classification
                stage.step("Classifying document vertical (go/legal/judicial/data/scheme)")
                vertical_result = self.vertical_classifier.classify(cleaned_text, file_path.name)
                vertical = vertical_result["vertical"]
                vertical_confidence = vertical_result["confidence"]
                method = vertical_result.get("method", "unknown")
                
                stage.metric("Vertical", vertical)
                stage.metric("Confidence", f"{vertical_confidence:.2%}")
                stage.metric("Classification method", method)
                if "reasoning" in vertical_result:
                    stage.metric("Reasoning", vertical_result["reasoning"])
                
                stage.success(f"Vertical classification: '{vertical}' ({vertical_confidence:.2%} confidence)")
                
                # Detailed document classification
                stage.step(f"Classifying document type within '{vertical}' vertical")
                doc_classification = self.doc_classifier.classify(
                    cleaned_text[:2000], 
                    vertical, 
                    file_path.name
                )
                doc_type = doc_classification["doc_type"]
                doc_confidence = doc_classification.get("confidence", 0.0)
                category = doc_classification.get("category", "unknown")
                
                stage.metric("Document type", doc_type)
                stage.metric("Type confidence", f"{doc_confidence:.2%}")
                stage.metric("Category", category)
                
                stage.success(f"Document type: '{doc_type}' ({doc_confidence:.2%} confidence)")
            
            # ================================================================
            # STAGE 4: STRUCTURE PARSING
            # ================================================================
            with StageLogger(logger, "STAGE 4: STRUCTURE PARSING") as stage:
                parser = self.structure_parsers.get(vertical)
                
                if parser:
                    stage.step(f"Parsing {vertical} document structure")
                    # Pass word_coords to GO parser for visual anchoring
                    if vertical == "go":
                        # Construct basic OCR metadata from extraction stats
                        ocr_metadata = {
                            "engine": "tesseract" if extraction_result.get("needs_ocr") else "native", 
                            "confidence": 1.0 if not extraction_result.get("needs_ocr") else 0.85, # Proxy
                            "warnings": []
                        }
                        structure = parser.parse(cleaned_text, word_coords, ocr_metadata)
                    else:
                        structure = parser.parse(cleaned_text)
                        
                    has_structure = structure.get('has_structure', False)
                    stage.metric("Structure detected", "Yes" if has_structure else "No")
                    
                    if has_structure:
                        # Log structure-specific metrics
                        if vertical == "go":
                             identity = structure.get("identity", {})
                             if identity.get("go_number"):
                                 stage.metric("GO Number", identity["go_number"])
                             stage.metric("Doc Authority", identity.get("document_authority", "unknown"))
                        
                        if "hierarchical_orders" in structure:
                            stage.metric("Hierarchical paras", len(structure["hierarchical_orders"]))
                        if "section_count" in structure:
                            stage.metric("Section count", structure["section_count"])
                    
                    stage.success(f"Structure parsing complete: {has_structure}")
                else:
                    stage.warning(f"No structure parser available for vertical: {vertical}")
                    structure = {"has_structure": False}
            
            # ================================================================
            # STAGE 5: CHUNKING
            # ================================================================
            with StageLogger(logger, "STAGE 5: DOCUMENT CHUNKING") as stage:
                chunker = self.chunkers.get(vertical)
                
                if not chunker:
                    stage.error(f"No chunker available for vertical: {vertical}")
                    return {"status": "failed", "stage": "chunking", "doc_id": doc_id}
                
                # Build document metadata for chunking
                doc_metadata = {
                    "doc_id": doc_id,
                    "vertical": vertical,
                    "doc_type": doc_type,
                    "file_name": file_path.name
                }
                
                # Add extraction table info to metadata
                extracted_tables = extraction_result.get("tables", [])
                if extracted_tables:
                    doc_metadata["extracted_tables"] = extracted_tables
                    doc_metadata["table_count_extracted"] = len(extracted_tables)
                
                # Add structure info to metadata
                if structure.get("has_structure"):
                    if vertical == "go":
                        # Pass entire structure for strict parsing
                        doc_metadata["go_structure"] = structure
                        
                        # Add top-level identity for easier access
                        identity = structure.get("identity", {})
                        if identity:
                             doc_metadata["go_number"] = identity.get("go_number")
                             doc_metadata["go_year"] = identity.get("year")
                             doc_metadata["document_authority"] = identity.get("document_authority")

                    elif vertical == "legal" and "act_name" in structure:
                        doc_metadata["act_name"] = structure["act_name"]
                    elif vertical == "judicial":
                        if "case_number" in structure:
                            doc_metadata["case_number"] = structure["case_number"]
                        if "court" in structure:
                            doc_metadata["court"] = structure["court"]
                    elif vertical == "scheme" and "scheme_name" in structure:
                        doc_metadata["scheme_name"] = structure["scheme_name"]
                    
                    # Add structured tables for data documents
                    if vertical == "data" and "structured_tables" in structure:
                        doc_metadata["structured_tables"] = structure["structured_tables"]
                        doc_metadata["table_count_structured"] = len(structure.get("structured_tables", []))
                
                stage.step(f"Chunking document using {vertical}-specific chunker")
                stage.metric("Chunker type", f"{vertical}_chunker")
                stage.metric("Input text length", f"{len(cleaned_text):,} characters")
                
                chunks = chunker.chunk(cleaned_text, doc_id, doc_metadata)
                
                if not chunks:
                    stage.error("No chunks created - chunking failed")
                    return {"status": "failed", "stage": "chunking", "doc_id": doc_id, "error": "No chunks"}
                
                # Calculate chunk statistics
                total_chunk_words = sum(chunk.word_count if hasattr(chunk, 'word_count') else len(chunk.content.split()) for chunk in chunks)
                avg_chunk_words = total_chunk_words / len(chunks) if chunks else 0
                chunk_sizes = [len(chunk.content) if hasattr(chunk, 'content') else len(str(chunk)) for chunk in chunks]
                min_chunk_size = min(chunk_sizes) if chunk_sizes else 0
                max_chunk_size = max(chunk_sizes) if chunk_sizes else 0
                avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
                
                stage.metric("Total chunks created", len(chunks))
                stage.metric("Total words in chunks", total_chunk_words)
                stage.metric("Average words per chunk", f"{avg_chunk_words:.1f}")
                stage.metric("Min chunk size", f"{min_chunk_size:,} chars")
                stage.metric("Max chunk size", f"{max_chunk_size:,} chars")
                stage.metric("Average chunk size", f"{avg_chunk_size:,.0f} chars")
                
                stage.success(f"Chunking complete: {len(chunks)} chunks created")
            
            # ================================================================
            # STAGE 6: ENTITY EXTRACTION
            # ================================================================
            with StageLogger(logger, "STAGE 6: ENTITY EXTRACTION") as stage:
                stage.step("Extracting entities from document text")
                entities, relations_from_entities = self.entity_extractor.extract(cleaned_text, vertical, doc_id)
                
                # NEW: Extract policy domains for subject-matter scoping (Change 3)
                policy_domains = self.domain_extractor.extract_domains(cleaned_text)
                entities["policy_domains"] = policy_domains
                stage.metric("Policy domains", ", ".join(policy_domains) if policy_domains else "none")
                
                # Merge entities from relations if any (optional, usually entities is enough)
                entity_count = sum(len(v) if isinstance(v, list) else 0 for v in entities.values())
                entity_types = len([k for k, v in entities.items() if v and len(v) > 0])
                
                stage.metric("Total entities extracted", entity_count)
                stage.metric("Entity types found", entity_types)
                
                # Log entity type breakdown
                for entity_type, entity_list in entities.items():
                    if entity_list and len(entity_list) > 0:
                        stage.metric(f"  {entity_type}", len(entity_list))
                        # Show first few examples
                        examples = entity_list[:3]
                        if len(examples) > 0:
                            examples_str = ", ".join(str(e)[:50] for e in examples)
                            if len(entity_list) > 3:
                                examples_str += f" ... (+{len(entity_list)-3} more)"
                            stage.metric(f"    Examples", examples_str)
                
                stage.success(f"Entity extraction complete: {entity_count} entities across {entity_types} types")
            
            # ================================================================
            # STAGE 7: RELATION EXTRACTION
            # ================================================================
            with StageLogger(logger, "STAGE 7: RELATION EXTRACTION") as stage:
                relations = []
                
                # Only extract relations for important verticals
                if should_extract_relations(vertical, len(cleaned_text)):
                    stage.step("Extracting document relations (supersedes, amends, cites, etc.)")
                    relations_list = self.relation_extractor.extract_relations(
                        cleaned_text, 
                        doc_id, 
                        vertical,
                        entities=entities
                    )
                    relations = self.relation_extractor.relations_to_dict(relations_list)
                    
                    # Merge with relations from entity extraction (the new GORelationExtractor)
                    if relations_from_entities:
                        # Deduplicate or just add
                        relations.extend(relations_from_entities)

                    stage.metric("Total relations extracted", len(relations))
                    
                    # Group by relation type
                    relation_types = {}
                    for rel in relations:
                        rel_type = rel.get("relation_type", "unknown")
                        relation_types[rel_type] = relation_types.get(rel_type, 0) + 1
                    
                    for rel_type, count in relation_types.items():
                        stage.metric(f"  {rel_type}", count)
                        # Show examples
                        examples = [r for r in relations if r.get("relation_type") == rel_type][:2]
                        for ex in examples:
                            target = ex.get("target", "")[:60]
                            stage.metric(f"    → {target}", "")
                    
                    stage.success(f"Relation extraction complete: {len(relations)} relations found")
                else:
                    stage.step(f"Skipping relation extraction (not enabled for '{vertical}' vertical)")
                    stage.metric("Reason", f"Vertical '{vertical}' not in relation-enabled verticals")
                    stage.success("Relation extraction skipped")
                
                # Register GO for lineage tracking
                if vertical == "go":
                    go_number = doc_metadata.get("go_number") or entities.get("go_numbers", [None])[0]
                    if go_number:
                        self.go_chain_builder.add_go(go_number, doc_metadata, relations)

                # NEW: COMPUTE LEGAL STATUS
                stage.step("Computing legal status and authority weight")
                legal_status = self.legal_resolver.compute_document_status(doc_id, vertical, relations)
                stage.metric("Legal weight", f"{legal_status.get('legal_weight', 1.0):.2f}")
                stage.metric("Authority weight", f"{legal_status.get('authority_weight', 0.5):.2f}")
                stage.metric("Lineage links", len(legal_status.get("legal_lineage", {}).get("previous", [])))
            
            # ================================================================
            # STAGE 8: METADATA BUILDING
            # ================================================================
            with StageLogger(logger, "STAGE 8: METADATA BUILDING") as stage:
                stage.step("Converting chunks to dictionary format")
                
                # Convert chunks to dicts if they're Chunk objects
                chunk_dicts = []
                for i, chunk in enumerate(chunks):
                    if hasattr(chunk, '__dict__'):
                        # It's a Chunk object
                        chunk_dict = {
                            "content": chunk.content,
                            "text": chunk.content,  # Duplicate for compatibility
                            "chunk_id": chunk.chunk_id,
                            "doc_id": chunk.doc_id,
                            "chunk_index": chunk.chunk_index,
                            "word_count": chunk.word_count,
                            "metadata": chunk.metadata
                        }
                    else:
                        # Already a dict
                        chunk_dict = chunk
                        
                        # Ensure required fields
                        if "text" not in chunk_dict and "content" in chunk_dict:
                            chunk_dict["text"] = chunk_dict["content"]
                        if "content" not in chunk_dict and "text" in chunk_dict:
                            chunk_dict["content"] = chunk_dict["text"]
                    
                    # Build complete metadata for this chunk
                    chunk_metadata = self.metadata_builder.build_chunk_metadata(
                        chunk=chunk_dict,
                        doc_metadata=doc_metadata,
                        entities=entities,
                        relations=relations,
                        vertical=vertical,
                        legal_status=legal_status if 'legal_status' in locals() else None,
                        policy_domains=entities.get("policy_domains", [])
                    )
                    
                    # Add metadata to chunk
                    chunk_dict["metadata"] = chunk_metadata
                    chunk_dicts.append(chunk_dict)
                
                stage.metric("Chunks processed", len(chunk_dicts))
                stage.metric("Metadata fields per chunk", len(chunk_dicts[0]["metadata"]) if chunk_dicts else 0)
                
                stage.success(f"Metadata building complete: {len(chunk_dicts)} chunks with metadata")
            
            # ================================================================
            # STAGE 9: WRITE OUTPUTS
            # ================================================================
            with StageLogger(logger, "STAGE 9: WRITING OUTPUTS") as stage:
                # Get output paths
                output_paths = self.dir_manager.get_output_paths(vertical, doc_id)
                stage.metric("Output directory", str(output_paths["doc_dir"]))
                
                # Write raw text
                stage.step("Writing raw extracted text")
                write_text(text, output_paths["raw_text"])
                stage.metric("  raw_text.txt", f"{output_paths['raw_text'].stat().st_size:,} bytes")
                
                # Write cleaned text
                stage.step("Writing cleaned text")
                cleaned_text_path = output_paths.get("cleaned_text", output_paths["doc_dir"] / "cleaned_text.txt")
                write_text(cleaned_text, cleaned_text_path)
                stage.metric("  cleaned_text.txt", f"{cleaned_text_path.stat().st_size:,} bytes")
                
                # Write chunks as JSONL
                stage.step("Writing chunks (JSONL format)")
                chunks_path = output_paths["doc_dir"] / "chunks.jsonl"
                write_jsonl(chunk_dicts, chunks_path)
                stage.metric("  chunks.jsonl", f"{chunks_path.stat().st_size:,} bytes ({len(chunk_dicts)} chunks)")
                
                # Write entities
                stage.step("Writing entities")
                entities_path = output_paths["doc_dir"] / "entities.json"
                logger.info(f"DEBUG PIPELINE: entities keys for {doc_id}: {list(entities.keys())}")
                if "go_archetype" in entities:
                    logger.info(f"DEBUG PIPELINE: go_archetype value: {entities['go_archetype']}")
                write_json(entities, entities_path)
                stage.metric("  entities.json", f"{entities_path.stat().st_size:,} bytes")
                
                # Write relations
                if relations:
                    stage.step("Writing relations")
                    relations_path = output_paths["doc_dir"] / "relations.json"
                    write_json(relations, relations_path)
                    stage.metric("  relations.json", f"{relations_path.stat().st_size:,} bytes ({len(relations)} relations)")
                else:
                    stage.step("Skipping relations.json (no relations found)")
                
                # Write structure info
                stage.step("Writing structure information")
                structure_path = output_paths["doc_dir"] / "structure.json"
                structure_serializable = _make_json_serializable(structure)
                write_json(structure_serializable, structure_path)
                stage.metric("  structure.json", f"{structure_path.stat().st_size:,} bytes")
                
                # Write document metadata
                stage.step("Writing document metadata")
                doc_summary = self.metadata_builder.build_document_metadata(
                    doc_id=doc_id,
                    file_path=str(file_path),
                    vertical=vertical,
                    entities=entities,
                    relations=relations,
                    chunks_count=len(chunk_dicts)
                )
                doc_summary["doc_type"] = doc_type
                doc_summary["classification"] = doc_classification
                doc_summary["structure"] = _make_json_serializable(structure)
                
                metadata_path = output_paths["doc_dir"] / "metadata.json"
                write_json(doc_summary, metadata_path)
                stage.metric("  metadata.json", f"{metadata_path.stat().st_size:,} bytes")
                
                stage.success(f"All outputs written to: {output_paths['doc_dir']}")
            
            # ================================================================
            # COMPLETE
            # ================================================================
            processing_time = time.time() - start_time
            
            result = {
                "status": "success",
                "doc_id": doc_id,
                "vertical": vertical,
                "doc_type": doc_type,
                "confidence": vertical_confidence,
                "word_count": len(cleaned_text.split()),
                "chunks_count": len(chunk_dicts),
                "entities_count": entity_count,
                "relations_count": len(relations),
                "processing_time": processing_time,
                "output_dir": str(output_paths["doc_dir"]),
            }
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ DOCUMENT PROCESSING COMPLETE")
            logger.info(f"{'='*80}")
            logger.info(f"Document: {file_path.name}")
            logger.info(f"Processing time: {processing_time:.2f} seconds")
            logger.info(f"")
            logger.info(f"Results Summary:")
            logger.info(f"  • Vertical: {vertical} (confidence: {vertical_confidence:.2%})")
            logger.info(f"  • Document Type: {doc_type}")
            logger.info(f"  • Words: {len(cleaned_text.split()):,}")
            logger.info(f"  • Chunks: {len(chunk_dicts)}")
            logger.info(f"  • Entities: {entity_count} across {len([k for k, v in entities.items() if v])} types")
            logger.info(f"  • Relations: {len(relations)}")
            logger.info(f"  • Output: {output_paths['doc_dir']}")
            logger.info(f"{'='*80}\n")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "doc_id": doc_id if 'doc_id' in locals() else "unknown",
                "stage": "unknown"
            }
    
    def process_batch(
        self,
        input_dir: Optional[Path] = None,
        gcs_prefix: Optional[str] = None,
        max_docs: Optional[int] = None
    ) -> List[Dict]:
        """
        Process all documents from GCS or local directory.
        
        Args:
            input_dir: Local input directory (if using local file loader)
            gcs_prefix: GCS path prefix (e.g., "documents/go/") - for GCS loader
            max_docs: Maximum documents to process (None for all)
            
        Returns:
            List of processing results
        """
        logger.info(f"\n{'#'*60}")
        if hasattr(self.file_loader, 'bucket_name'):  # GCS loader
            if not gcs_prefix:
                gcs_prefix = "documents/"  # Default prefix
            logger.info(f"BATCH PROCESSING FROM GCS: {gcs_prefix}")
            file_infos = self.file_loader.load_batch(prefix=gcs_prefix, max_files=max_docs)
        else:
            if not input_dir:
                raise ValueError("input_dir required when using local file loader")
            logger.info(f"BATCH PROCESSING: {input_dir}")
            file_infos = self.file_loader.load_batch(input_dir)
            if max_docs:
                file_infos = file_infos[:max_docs]
        logger.info(f"{'#'*60}\n")
        
        logger.info(f"📁 Found {len(file_infos)} documents to process")
        
        results = []
        start_time = time.time()
        
        for i, file_info in enumerate(file_infos, 1):
            logger.info(f"\n{'─'*60}")
            logger.info(f"[{i}/{len(file_infos)}] Processing document...")
            logger.info(f"{'─'*60}")
            
            file_path = Path(file_info["path"])
            result = self.process_document(file_path)
            results.append(result)
            
            # Cleanup temp file if from GCS
            if hasattr(self.file_loader, 'cleanup_temp_file'):
                self.file_loader.cleanup_temp_file(file_info)
        
        # Summary
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["status"] == "success")
        fail_count = len(results) - success_count
        
        # Calculate statistics
        successful_results = [r for r in results if r["status"] == "success"]
        if successful_results:
            total_chunks = sum(r.get("chunks_count", 0) for r in successful_results)
            total_entities = sum(r.get("entities_count", 0) for r in successful_results)
            total_relations = sum(r.get("relations_count", 0) for r in successful_results)
            avg_time = sum(r.get("processing_time", 0) for r in successful_results) / len(successful_results)
        else:
            total_chunks = total_entities = total_relations = avg_time = 0
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total: {len(results)} documents")
        logger.info(f"Success: {success_count} | Failed: {fail_count}")
        logger.info(f"Total time: {total_time:.1f}s | Avg: {avg_time:.1f}s/doc")
        logger.info(f"Total chunks: {total_chunks}")
        logger.info(f"Total entities: {total_entities}")
        logger.info(f"Total relations: {total_relations}")
        logger.info(f"{'='*60}\n")
        
        return results


def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingestion Pipeline V2")
    parser.add_argument("--input", type=str, required=True, help="Input directory or file")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--max-docs", type=int, default=None, help="Max documents to process")
    
    args = parser.parse_args()
    
    # Setup enhanced logging
    from backend.ingestion.config.settings import LOG_LEVEL, LOG_FILE
    setup_logging(
        level=LOG_LEVEL,
        log_file=LOG_FILE if LOG_FILE else None,
        use_colors=True
    )
    
    # Initialize pipeline
    pipeline = IngestionPipeline(output_dir=Path(args.output) if args.output else None)
    
    # Process
    input_path = Path(args.input)
    if input_path.is_file():
        result = pipeline.process_document(input_path)
        print(f"\nResult: {result}")
    elif input_path.is_dir():
        results = pipeline.process_batch(input_path, max_docs=args.max_docs)
        print(f"\nProcessed {len(results)} documents")
    else:
        print(f"Error: {input_path} is not a valid file or directory")


if __name__ == "__main__":
    main()