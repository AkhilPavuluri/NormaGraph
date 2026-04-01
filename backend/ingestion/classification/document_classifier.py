"""
Document Classifier
Classifies documents into specific types within verticals
Examples: Act, Rule, Amendment, Notification, Order, Judgment, etc.
"""
import re
import logging
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Detailed document types"""
    # GO types
    GO_ORDER = "go_order"
    GO_NOTIFICATION = "go_notification"
    GO_CIRCULAR = "go_circular"
    
    # Legal types
    ACT = "act"
    RULE = "rule"
    REGULATION = "regulation"
    AMENDMENT = "amendment"
    NOTIFICATION = "notification"
    
    # Judicial types
    JUDGMENT = "judgment"
    ORDER = "order"
    INTERIM_ORDER = "interim_order"
    
    # Data types
    REPORT = "report"
    STATISTICS = "statistics"
    BUDGET = "budget"
    
    # Scheme types
    SCHEME_DOCUMENT = "scheme_document"
    GUIDELINES = "guidelines"
    
    # Unknown
    UNKNOWN = "unknown"


class DocumentClassifier:
    """
    Classifies documents into specific types
    
    Uses:
    - Fast rule-based classification (always)
    - Optional LLM classification (for ambiguous cases)
    """
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize classifier
        
        Args:
            use_llm: Whether to use LLM for ambiguous cases
        """
        self.use_llm = use_llm
        self._compile_patterns()
        
        logger.info(f"Document classifier initialized - LLM: {use_llm}")
    
    def _compile_patterns(self):
        """Compile classification patterns"""
        
        # Act patterns
        self.act_patterns = [
            re.compile(r'(?:The\s+)?([A-Z][A-Za-z\s,\(\)]+)\s+Act(?:,?\s+\d{4})?', re.IGNORECASE),
            re.compile(r'An\s+Act\s+to', re.IGNORECASE),
            re.compile(r'BE\s+IT\s+ENACTED', re.IGNORECASE)
        ]
        
        # Rule patterns
        self.rule_patterns = [
            re.compile(r'(?:The\s+)?([A-Z][A-Za-z\s,\(\)]+)\s+Rules(?:,?\s+\d{4})?', re.IGNORECASE),
            re.compile(r'In\s+exercise\s+of\s+the\s+powers', re.IGNORECASE),
            re.compile(r'pursuant\s+to\s+Section', re.IGNORECASE)
        ]
        
        # Amendment patterns
        self.amendment_patterns = [
            re.compile(r'Amendment', re.IGNORECASE),
            re.compile(r'amends?\s+(?:the\s+)?(?:Act|Rules?)', re.IGNORECASE),
            re.compile(r'in\s+(?:partial\s+)?amendment', re.IGNORECASE)
        ]
        
        # GO patterns
        self.go_patterns = [
            re.compile(r'Government\s+Order', re.IGNORECASE),
            re.compile(r'G\.?O\.?\s*(?:MS|RT)', re.IGNORECASE)
        ]
        
        # Notification patterns
        self.notification_patterns = [
            re.compile(r'NOTIFICATION', re.IGNORECASE),
            re.compile(r'(?:is|are)\s+hereby\s+notified', re.IGNORECASE)
        ]
        
        # Circular patterns
        self.circular_patterns = [
            re.compile(r'CIRCULAR', re.IGNORECASE),
            re.compile(r'for\s+information\s+and\s+(?:compliance|guidance)', re.IGNORECASE)
        ]
        
        # Judgment patterns
        self.judgment_patterns = [
            re.compile(r'JUDGMENT', re.IGNORECASE),
            re.compile(r'CORAM[:\s]', re.IGNORECASE),
            re.compile(r'(?:Hon\'ble|Honourable)\s+(?:Justice|Judge)', re.IGNORECASE),
            re.compile(r'(?:Petitioner|Appellant)\s+(?:Vs?\.?|versus)\s+(?:Respondent|Defendant)', re.IGNORECASE)
        ]
        
        # Order patterns (judicial)
        self.order_patterns = [
            re.compile(r'ORDER', re.IGNORECASE),
            re.compile(r'the\s+(?:Court|Bench)\s+(?:orders?|directs?)', re.IGNORECASE)
        ]
        
        # Report patterns
        self.report_patterns = [
            re.compile(r'(?:Annual|Quarterly|Monthly)\s+Report', re.IGNORECASE),
            re.compile(r'REPORT\s+(?:ON|OF)', re.IGNORECASE),
            re.compile(r'Executive\s+Summary', re.IGNORECASE)
        ]
        
        # Budget patterns
        self.budget_patterns = [
            re.compile(r'Budget\s+(?:Estimates?|Allocations?)', re.IGNORECASE),
            re.compile(r'Financial\s+(?:Statement|Estimates?)', re.IGNORECASE)
        ]
        
        # Scheme patterns
        self.scheme_patterns = [
            re.compile(r'Scheme\s+(?:for|of)', re.IGNORECASE),
            re.compile(r'(?:Eligibility|Benefits?)\s+under\s+the\s+scheme', re.IGNORECASE),
            re.compile(r'Implementation\s+of\s+(?:the\s+)?scheme', re.IGNORECASE)
        ]
        
        # Guidelines patterns
        self.guidelines_patterns = [
            re.compile(r'GUIDELINES?', re.IGNORECASE),
            re.compile(r'Standard\s+Operating\s+Procedures?', re.IGNORECASE),
            re.compile(r'Instructions?\s+for', re.IGNORECASE)
        ]
    
    def classify(
        self, 
        text: str, 
        vertical: str,
        file_name: str = ""
    ) -> Dict:
        """
        Classify document into specific type
        
        Args:
            text: Document text (first 2000 chars usually enough)
            vertical: Already determined vertical (go, legal, judicial, etc.)
            file_name: Optional file name
            
        Returns:
            Dictionary with classification results
        """
        if not text:
            return {
                "doc_type": DocumentType.UNKNOWN.value,
                "confidence": 0.0,
                "vertical": vertical
            }
        
        # Use first 2000 chars for classification
        text_sample = text[:2000]
        
        # Classify based on vertical
        if vertical == "go":
            doc_type, confidence = self._classify_go(text_sample)
        elif vertical == "legal":
            doc_type, confidence = self._classify_legal(text_sample)
        elif vertical == "judicial":
            doc_type, confidence = self._classify_judicial(text_sample)
        elif vertical == "data":
            doc_type, confidence = self._classify_data(text_sample, file_name)
        elif vertical == "scheme":
            doc_type, confidence = self._classify_scheme(text_sample)
        else:
            doc_type = DocumentType.UNKNOWN
            confidence = 0.5
        
        return {
            "doc_type": doc_type.value,
            "confidence": confidence,
            "vertical": vertical,
            "category": self._get_category(doc_type)
        }
    
    def _classify_go(self, text: str) -> tuple:
        """Classify GO document"""
        # Check for circular
        if any(p.search(text) for p in self.circular_patterns):
            return DocumentType.GO_CIRCULAR, 0.85
        
        # Check for notification
        if any(p.search(text) for p in self.notification_patterns):
            return DocumentType.GO_NOTIFICATION, 0.80
        
        # Default to order
        return DocumentType.GO_ORDER, 0.75
    
    def _classify_legal(self, text: str) -> tuple:
        """Classify legal document"""
        # Check for amendment first
        if any(p.search(text) for p in self.amendment_patterns):
            return DocumentType.AMENDMENT, 0.90
        
        # Check for Act
        if any(p.search(text) for p in self.act_patterns):
            return DocumentType.ACT, 0.90
        
        # Check for Rule
        if any(p.search(text) for p in self.rule_patterns):
            return DocumentType.RULE, 0.85
        
        # Check for Notification
        if any(p.search(text) for p in self.notification_patterns):
            return DocumentType.NOTIFICATION, 0.80
        
        # Check for Regulation
        if 'regulation' in text.lower()[:500]:
            return DocumentType.REGULATION, 0.75
        
        # Default
        return DocumentType.UNKNOWN, 0.50
    
    def _classify_judicial(self, text: str) -> tuple:
        """Classify judicial document"""
        # Check for judgment
        if any(p.search(text) for p in self.judgment_patterns):
            return DocumentType.JUDGMENT, 0.90
        
        # Check for order
        if any(p.search(text) for p in self.order_patterns):
            # Check if interim
            if 'interim' in text.lower()[:500]:
                return DocumentType.INTERIM_ORDER, 0.85
            return DocumentType.ORDER, 0.85
        
        # Default to order
        return DocumentType.ORDER, 0.70
    
    def _classify_data(self, text: str, file_name: str) -> tuple:
        """Classify data document"""
        # Check file name first
        if file_name:
            file_lower = file_name.lower()
            if 'budget' in file_lower:
                return DocumentType.BUDGET, 0.90
            if any(word in file_lower for word in ['report', 'annual', 'quarterly']):
                return DocumentType.REPORT, 0.85
            if any(word in file_lower for word in ['stats', 'statistics', 'data']):
                return DocumentType.STATISTICS, 0.85
        
        # Check content
        if any(p.search(text) for p in self.budget_patterns):
            return DocumentType.BUDGET, 0.85
        
        if any(p.search(text) for p in self.report_patterns):
            return DocumentType.REPORT, 0.80
        
        # Check for tables/statistics
        if text.count('Table') + text.count('|') + text.count('\t') > 10:
            return DocumentType.STATISTICS, 0.75
        
        # Default to report
        return DocumentType.REPORT, 0.70
    
    def _classify_scheme(self, text: str) -> tuple:
        """Classify scheme document"""
        # Check for guidelines
        if any(p.search(text) for p in self.guidelines_patterns):
            return DocumentType.GUIDELINES, 0.85
        
        # Default to scheme document
        if any(p.search(text) for p in self.scheme_patterns):
            return DocumentType.SCHEME_DOCUMENT, 0.80
        
        return DocumentType.SCHEME_DOCUMENT, 0.75
    
    def _get_category(self, doc_type: DocumentType) -> str:
        """Get high-level category from document type"""
        categories = {
            DocumentType.GO_ORDER: "government_order",
            DocumentType.GO_NOTIFICATION: "government_order",
            DocumentType.GO_CIRCULAR: "government_order",
            DocumentType.ACT: "legislation",
            DocumentType.RULE: "legislation",
            DocumentType.REGULATION: "legislation",
            DocumentType.AMENDMENT: "legislation",
            DocumentType.NOTIFICATION: "notification",
            DocumentType.JUDGMENT: "judicial",
            DocumentType.ORDER: "judicial",
            DocumentType.INTERIM_ORDER: "judicial",
            DocumentType.REPORT: "data_report",
            DocumentType.STATISTICS: "data_report",
            DocumentType.BUDGET: "data_report",
            DocumentType.SCHEME_DOCUMENT: "scheme",
            DocumentType.GUIDELINES: "scheme"
        }
        
        return categories.get(doc_type, "unknown")
    
    def batch_classify(
        self, 
        documents: list, 
        vertical: str
    ) -> list:
        """
        Classify multiple documents
        
        Args:
            documents: List of dicts with 'text' and optionally 'file_name'
            vertical: Vertical for all documents
            
        Returns:
            List of classification results
        """
        results = []
        
        for doc in documents:
            text = doc.get('text', '')
            file_name = doc.get('file_name', '')
            
            result = self.classify(text, vertical, file_name)
            results.append(result)
        
        return results