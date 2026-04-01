"""
Policy Domain Extractor
=======================
Extracts the policy domain (transfer, promotion, salary, etc.) from GO text
using regex and keyword matching.
"""

import re
import logging
from typing import List, Set

logger = logging.getLogger(__name__)

DOMAIN_KEYWORDS = {
    "transfer": [
        "transfer", "postings", "deputation", "relieved", "joining",
        "counseling", "mutual transfer", "request transfer", "spousal category"
    ],
    "promotion": [
        "promotion", "upgradation", "panel", "seniority list", "eligible for promotion",
        "adhoc promotion", "regularization of services"
    ],
    "salary": [
        "salary", "pay scale", "allowance", "da", "hra", "increment",
        "arrears", "revised pay scales", "rps", "fixation of pay"
    ],
    "leave": [
        "leave", "casual leave", "earned leave", "maternity leave",
        "medical leave", "child care leave", "ccl", "surrender leave"
    ],
    "discipline": [
        "disciplinary", "suspension", "enquiry", "charge sheet", "penalty",
        "show cause notice", "reinstatement", "cca rules"
    ],
    "appointment": [
        "appointment", "recruitment", "dsc", "selection", "interim relief",
        "compassionate appointment", "contract basis", "outsourcing"
    ],
    "retirement": [
        "retirement", "pension", "gratuity", "superannuation", "commutation",
        "pensionary benefits", "provisional pension"
    ]
}

class DomainExtractor:
    """
    Extracts policy domains from text using keywords.
    """
    
    def __init__(self):
        # Compile patterns for efficiency - modified to allow suffixes (Change 3 correction)
        self.patterns = {
            domain: re.compile(r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')(\w+)?\b', re.IGNORECASE)
            for domain, keywords in DOMAIN_KEYWORDS.items()
        }

    def extract_domains(self, text: str) -> List[str]:
        """
        Extract matching domains from text.
        """
        matches = []
        # Optimization: use a subset of text for domain detection (title/subject preferred)
        # But for now, we search everything as fallback.
        
        # Check title/subject lines more heavily if possible
        # For simplicity in this layer, we scan the whole text but keep results unique
        
        for domain, pattern in self.patterns.items():
            if pattern.search(text):
                matches.append(domain)
        
        return matches

    def get_primary_domain(self, text: str) -> str:
        """
        Attempts to find the single most relevant domain (e.g. from counting matches).
        """
        counts = {}
        for domain, pattern in self.patterns.items():
            found = pattern.findall(text)
            if found:
                counts[domain] = len(found)
        
        if not counts:
            return "general"
            
        return max(counts, key=counts.get)
