"""
Canonical ID Generator

FROZEN FORMATS - DO NOT CHANGE WITHOUT ARCHITECTURE REVIEW

This module defines the canonical, deterministic ID formats for documents and chunks.
These formats are FROZEN and must remain stable for:
- Vector search traceability
- Judicial relation integrity
- Cache key stability
- Historical answer reproducibility
"""

import re
import hashlib
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IDFormatError(Exception):
    """Raised when ID format validation fails"""
    pass


class DocumentIDGenerator:
    """
    Generates canonical document IDs.
    
    FORMAT (FROZEN):
    {doc_type}_{identifier}_{date}_{suffix?}
    
    Rules:
    - doc_type: go, judgment, regulation, policy, report
    - identifier: document-specific identifier (GO number, case number, etc.)
    - date: YYYY-MM-DD format
    - suffix: optional disambiguator (only if needed for uniqueness)
    
    Examples:
    - GO: go_123_2024-01-15
    - Judgment: judgment_sc_case123_2020-01-01
    - Regulation: regulation_ugc_2020-01-01
    """
    
    # Valid document types
    VALID_DOC_TYPES = {"go", "judgment", "regulation", "policy", "report"}
    
    @staticmethod
    def generate_go_id(go_number: str, date: str, jurisdiction: str = "AP") -> str:
        """
        Generate canonical GO document ID.
        
        Format: go_{jurisdiction}_{go_number}_{date}
        
        Args:
            go_number: GO number (e.g., "123")
            date: Date in YYYY-MM-DD format
            jurisdiction: Jurisdiction code (default: "AP")
            
        Returns:
            Canonical document ID (e.g., "go_AP_123_2024-01-15")
        """
        # Normalize GO number (remove spaces, special chars)
        go_number_clean = re.sub(r'[^A-Za-z0-9]', '', str(go_number))
        
        # Normalize date to YYYY-MM-DD
        date_normalized = DocumentIDGenerator._normalize_date(date)
        
        # Validate
        if not go_number_clean or go_number_clean == "UNKNOWN":
            raise IDFormatError(f"Invalid GO number: {go_number}")
        
        if not date_normalized:
            raise IDFormatError(f"Invalid date format: {date}")
        
        doc_id = f"go_{jurisdiction}_{go_number_clean}_{date_normalized}"
        
        # Validate format
        DocumentIDGenerator.validate_document_id(doc_id)
        
        return doc_id
    
    @staticmethod
    def generate_judgment_id(
        court: str,
        case_type: Optional[str],
        case_number: Optional[str],
        case_year: Optional[int],
        judgment_date: str,
        jurisdiction: str = "IN"
    ) -> str:
        """
        Generate canonical judgment document ID.
        
        Format: judgment_{court_code}_{case_type}_{case_no}_{case_year}_{judgment_date}
        
        This format prevents collisions from:
        - Same case number, different judgment types (interim/final/review)
        - Same case number, different years
        - Same case number, different benches
        
        Args:
            court: Court name (e.g., "Supreme Court" → "SC")
            case_type: Case type (WP, CA, AP, CMA, etc.)
            case_number: Case number (normalized)
            case_year: Year case was filed/registered
            judgment_date: Judgment date in YYYY-MM-DD format
            jurisdiction: Jurisdiction code (default: "IN" for India)
            
        Returns:
            Canonical document ID (e.g., "judgment_SC_WP_123_2019_2020-01-01")
        """
        # Normalize court code
        court_code = DocumentIDGenerator._normalize_court_code(court)
        
        # Normalize case type (required)
        if not case_type:
            raise IDFormatError("case_type is required for judgment IDs")
        case_type_clean = re.sub(r'[^A-Za-z0-9]', '', str(case_type).upper())[:10]
        if not case_type_clean:
            raise IDFormatError(f"Invalid case_type: {case_type}")
        
        # Normalize case number (required)
        if not case_number:
            raise IDFormatError("case_number is required for judgment IDs")
        # Aggressive normalization: uppercase, alphanumeric + underscore only
        case_number_clean = re.sub(r'[^A-Za-z0-9]', '_', str(case_number).upper())
        # Remove common prefixes
        case_number_clean = re.sub(r'^(NO|NO\.|OF|OF\.|CASE|CASE\.)\s*', '', case_number_clean, flags=re.IGNORECASE)
        case_number_clean = case_number_clean.strip('_')[:30]  # Limit length
        
        # Validate case year (required)
        if not case_year:
            raise IDFormatError("case_year is required for judgment IDs")
        if not isinstance(case_year, int) or case_year < 1900 or case_year > 2100:
            raise IDFormatError(f"Invalid case_year: {case_year}")
        
        # Normalize judgment date
        date_normalized = DocumentIDGenerator._normalize_date(judgment_date)
        if not date_normalized:
            raise IDFormatError(f"Invalid judgment_date format: {judgment_date}")
        
        doc_id = f"judgment_{court_code}_{case_type_clean}_{case_number_clean}_{case_year}_{date_normalized}"
        
        # Validate format
        DocumentIDGenerator.validate_document_id(doc_id)
        
        return doc_id
    
    @staticmethod
    def generate_regulation_id(
        authority: str,
        shortcode: Optional[str],
        date: str,
        regulation_number: Optional[str] = None
    ) -> str:
        """
        Generate canonical regulation document ID.
        
        Format: regulation_{authority_code}_{shortcode}_{date}
        
        Shortcode is a stable slug derived from regulation title/topic.
        This prevents collisions when multiple regulations are issued on the same date.
        
        Args:
            authority: Authority name (e.g., "UGC", "AICTE")
            shortcode: Stable shortcode/slug (e.g., "AUTONOMY", "FEE", "ADMISSION")
            date: Date in YYYY-MM-DD format
            regulation_number: Optional regulation number (used if shortcode not available)
            
        Returns:
            Canonical document ID (e.g., "regulation_UGC_AUTONOMY_2018-07-12")
        """
        # Normalize authority code
        authority_code = re.sub(r'[^A-Za-z0-9]', '', str(authority).upper())[:20]
        
        # Normalize shortcode (required)
        if shortcode:
            # Create stable slug: uppercase, alphanumeric + underscore only
            shortcode_clean = re.sub(r'[^A-Za-z0-9]', '_', str(shortcode).upper())
            shortcode_clean = shortcode_clean.strip('_')[:30]
        elif regulation_number:
            # Fallback: use regulation number as shortcode
            shortcode_clean = re.sub(r'[^A-Za-z0-9]', '_', str(regulation_number).upper())[:30]
        else:
            raise IDFormatError("Either shortcode or regulation_number is required for regulation IDs")
        
        if not shortcode_clean:
            raise IDFormatError("Invalid shortcode: cannot be empty after normalization")
        
        # Normalize date
        date_normalized = DocumentIDGenerator._normalize_date(date)
        
        if not date_normalized:
            raise IDFormatError(f"Invalid date format: {date}")
        
        doc_id = f"regulation_{authority_code}_{shortcode_clean}_{date_normalized}"
        
        # Validate format
        DocumentIDGenerator.validate_document_id(doc_id)
        
        return doc_id
    
    @staticmethod
    def validate_document_id(doc_id: str) -> bool:
        """
        Validate document ID format with strict rules.
        
        Raises:
            IDFormatError if format is invalid
        
        Hard failures for:
        - Invalid court_code (for judgments)
        - Invalid date format
        - Unknown doc_type
        """
        if not doc_id:
            raise IDFormatError("Document ID cannot be empty")
        
        # Check format: {doc_type}_{identifier}_{date} or {doc_type}_{...}_{date}
        parts = doc_id.split('_')
        if len(parts) < 3:
            raise IDFormatError(f"Invalid document ID format: {doc_id}. Expected: {{doc_type}}_{{identifier}}_{{date}}")
        
        doc_type = parts[0]
        if doc_type not in DocumentIDGenerator.VALID_DOC_TYPES:
            raise IDFormatError(
                f"Invalid doc_type: {doc_type}. Must be one of {DocumentIDGenerator.VALID_DOC_TYPES}. "
                f"This is a HARD FAILURE - document will be rejected."
            )
        
        # Check date format (last part should be YYYY-MM-DD)
        date_part = parts[-1]
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_part):
            raise IDFormatError(
                f"Invalid date format in ID: {date_part}. Expected YYYY-MM-DD. "
                f"This is a HARD FAILURE - document will be rejected."
            )
        
        # Special validation for judgments (must have court_code)
        if doc_type == "judgment":
            if len(parts) < 6:  # judgment_{court}_{type}_{case}_{year}_{date}
                raise IDFormatError(
                    f"Invalid judgment ID format: {doc_id}. "
                    f"Expected: judgment_{{court_code}}_{{case_type}}_{{case_no}}_{{case_year}}_{{date}}"
                )
            court_code = parts[1]
            valid_courts = {"SC", "HC", "DC", "TRIB"}
            if court_code not in valid_courts and len(court_code) > 5:
                logger.warning(f"Unusual court code in judgment ID: {court_code}")
        
        return True
    
    @staticmethod
    def _normalize_date(date_str: Optional[str]) -> Optional[str]:
        """Normalize date to YYYY-MM-DD format"""
        if not date_str:
            return None
        
        # Try various formats
        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y-%m",
            "%m-%Y"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # If only year, use first day of year
        if re.match(r'^\d{4}$', date_str):
            return f"{date_str}-01-01"
        
        return None
    
    @staticmethod
    def _normalize_court_code(court: str) -> str:
        """Normalize court name to code"""
        court_upper = court.upper()
        
        # Common mappings
        mappings = {
            "SUPREME COURT": "SC",
            "HIGH COURT": "HC",
            "DISTRICT COURT": "DC",
            "TRIBUNAL": "TRIB"
        }
        
        for key, code in mappings.items():
            if key in court_upper:
                return code
        
        # Fallback: use first 5 chars, uppercase, alphanumeric only
        return re.sub(r'[^A-Za-z0-9]', '', court_upper)[:5]


class ChunkIDGenerator:
    """
    Generates canonical chunk IDs.
    
    FORMAT (FROZEN):
    {document_id}_{chunk_type}_{sequence:03d}
    
    Rules:
    - document_id: Parent document ID (canonical format)
    - chunk_type: ratio, obiter, clause, section, paragraph, preamble
    - sequence: Zero-padded 3-digit sequence number (001, 002, etc.)
    
    Examples:
    - go_AP_123_2024-01-15_clause_001
    - judgment_SC_case123_2020-01-01_ratio_001
    - go_AP_123_2024-01-15_preamble_001
    """
    
    # Valid chunk types (FROZEN ENUM - DO NOT MODIFY WITHOUT MIGRATION PLAN)
    VALID_CHUNK_TYPES = {
        "preamble",  # Document preamble
        "clause",    # Legal clause
        "section",   # Section of act/regulation
        "ratio",     # Ratio decidendi (judicial)
        "obiter",    # Obiter dicta (judicial)
        "annexure"   # Annexure/appendix
    }
    
    # Chunk type mapping (for backward compatibility during migration)
    CHUNK_TYPE_MAP = {
        "clause": "clause",
        "para": "clause",  # Paragraphs map to clauses
        "para_no": "clause",
        "section": "section",
        "ratio": "ratio",
        "obiter": "obiter",
        "preamble": "preamble",
        "order": "clause",  # Orders map to clauses
        "annexure": "annexure"
    }
    
    @staticmethod
    def generate_chunk_id(
        document_id: str,
        chunk_type: str,
        sequence: int
    ) -> str:
        """
        Generate canonical chunk ID.
        
        Format: {document_id}_{chunk_type}_{sequence:03d}
        
        Args:
            document_id: Parent document ID (must be canonical format)
            chunk_type: Type of chunk (ratio, clause, etc.)
            sequence: Sequence number (0-indexed, will be 1-indexed in ID)
            
        Returns:
            Canonical chunk ID
        """
        # Validate document ID format
        try:
            DocumentIDGenerator.validate_document_id(document_id)
        except IDFormatError as e:
            raise IDFormatError(f"Invalid document_id for chunk: {e}")
        
        # Normalize chunk type (strict enum enforcement)
        chunk_type_lower = chunk_type.lower()
        if chunk_type_lower not in ChunkIDGenerator.VALID_CHUNK_TYPES:
            # Try mapping for backward compatibility
            chunk_type_lower = ChunkIDGenerator.CHUNK_TYPE_MAP.get(chunk_type_lower, None)
            if not chunk_type_lower:
                raise IDFormatError(
                    f"Invalid chunk_type: '{chunk_type}'. "
                    f"Must be one of {ChunkIDGenerator.VALID_CHUNK_TYPES}"
                )
            logger.warning(f"Chunk type '{chunk_type}' mapped to '{chunk_type_lower}' (backward compatibility)")
        
        # Validate sequence
        if sequence < 0:
            raise IDFormatError(f"Invalid sequence number: {sequence}. Must be >= 0")
        
        # Generate ID (sequence is 1-indexed in ID)
        chunk_id = f"{document_id}_{chunk_type_lower}_{sequence + 1:03d}"
        
        # Validate format
        ChunkIDGenerator.validate_chunk_id(chunk_id)
        
        return chunk_id
    
    @staticmethod
    def validate_chunk_id(chunk_id: str) -> bool:
        """
        Validate chunk ID format.
        
        Raises:
            IDFormatError if format is invalid
        """
        if not chunk_id:
            raise IDFormatError("Chunk ID cannot be empty")
        
        # Check format: {document_id}_{chunk_type}_{sequence}
        parts = chunk_id.split('_')
        if len(parts) < 4:  # At least doc_type, identifier, date, chunk_type, sequence
            raise IDFormatError(f"Invalid chunk ID format: {chunk_id}")
        
        # Extract sequence (last part)
        sequence_str = parts[-1]
        if not re.match(r'^\d{3}$', sequence_str):
            raise IDFormatError(f"Invalid sequence in chunk ID: {sequence_str}. Expected 3-digit number")
        
        # Extract chunk type (second to last)
        chunk_type = parts[-2]
        if chunk_type not in ChunkIDGenerator.VALID_CHUNK_TYPES:
            raise IDFormatError(
                f"Invalid chunk_type: {chunk_type}. Must be one of {ChunkIDGenerator.VALID_CHUNK_TYPES}. "
                f"This is a HARD FAILURE - chunk will be rejected."
            )
        
        # Validate document ID part (everything before chunk_type)
        document_id = '_'.join(parts[:-2])
        try:
            DocumentIDGenerator.validate_document_id(document_id)
        except IDFormatError as e:
            raise IDFormatError(f"Invalid document_id in chunk ID: {e}")
        
        return True
    
    @staticmethod
    def extract_document_id(chunk_id: str) -> str:
        """
        Extract document ID from chunk ID.
        
        Args:
            chunk_id: Canonical chunk ID
            
        Returns:
            Document ID
        """
        # Validate chunk ID first
        ChunkIDGenerator.validate_chunk_id(chunk_id)
        
        # Extract document ID (everything before last 2 parts: chunk_type and sequence)
        parts = chunk_id.split('_')
        # Document ID is everything except last 2 parts
        doc_id_parts = parts[:-2]
        return '_'.join(doc_id_parts)


def generate_fallback_document_id(
    doc_type: str,
    content_hash: str,
    date: Optional[str] = None
) -> str:
    """
    Generate fallback document ID when canonical identifiers are missing.
    
    Format: {doc_type}_unknown_{date}_{hash:8}
    
    ⚠️ WARNING: This should NEVER be used silently.
    
    Rules:
    - MUST log as ERROR
    - MUST flag needs_manual_resolution = true
    - MUST be stored separately for review
    
    Use ONLY when canonical identifiers cannot be extracted AND manual resolution is pending.
    """
    logger.error(
        f"⚠️ FALLBACK ID GENERATED for {doc_type}. "
        f"This document needs manual resolution. Hash: {content_hash[:8]}"
    )
    
    date_normalized = DocumentIDGenerator._normalize_date(date) if date else "unknown"
    hash_short = content_hash[:8]  # First 8 chars of hash
    
    fallback_id = f"{doc_type}_unknown_{date_normalized}_{hash_short}"
    
    # Log for manual resolution tracking
    logger.error(f"Fallback ID generated: {fallback_id} - REQUIRES MANUAL RESOLUTION")
    
    return fallback_id


def generate_fallback_chunk_id(
    document_id: str,
    chunk_type: str,
    text_hash: str,
    sequence: int
) -> str:
    """
    Generate fallback chunk ID when sequence is ambiguous.
    
    Format: {document_id}_{chunk_type}_{sequence:03d}_{hash:4}
    
    ⚠️ WARNING: This should NEVER be used silently.
    
    Rules:
    - MUST log as ERROR
    - MUST flag needs_manual_resolution = true
    - Sequence ambiguity indicates data quality issue
    
    Use ONLY when sequence cannot be determined deterministically AND manual resolution is pending.
    """
    logger.error(
        f"⚠️ FALLBACK CHUNK ID GENERATED for {document_id}. "
        f"Sequence ambiguity detected. Hash: {text_hash[:4]}"
    )
    
    hash_short = text_hash[:4]  # First 4 chars of hash
    fallback_id = f"{document_id}_{chunk_type}_{sequence + 1:03d}_{hash_short}"
    
    # Log for manual resolution tracking
    logger.error(f"Fallback chunk ID generated: {fallback_id} - REQUIRES MANUAL RESOLUTION")
    
    return fallback_id

