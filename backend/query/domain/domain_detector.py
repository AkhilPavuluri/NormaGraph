"""
Domain Detector

Detects which policy/legal domains are needed for a query.
Implements keyword-based domain triggering and domain layering.
"""
import re
import logging
from typing import Dict, List, Set, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class DomainLayer(Enum):
    """Domain layers for retrieval strategy"""
    PRIMARY = "primary"  # Core domain (always retrieved)
    BINDING_CONSTRAINTS = "binding_constraints"  # Constitutional, judicial constraints
    IMPACT_DOMAINS = "impact_domains"  # Labor, finance, social justice, etc.


@dataclass
class DetectedDomain:
    """A detected domain with its layer"""
    domain: str
    layer: DomainLayer
    confidence: float
    trigger_keywords: List[str]
    reason: str


class DomainDetector:
    """
    Detects which domains are needed for a query.
    
    Implements the domain-aware strategy:
    - Primary domain: Always retrieved (e.g., education)
    - Binding constraints: Constitutional, judicial (conditional)
    - Impact domains: Labor, finance, social justice (triggered by keywords)
    """
    
    # Domain keyword mappings
    DOMAIN_KEYWORDS = {
        # Constitutional domain
        "constitutional": {
            "keywords": [
                "reservation", "quota", "equality", "discrimination", "fundamental right",
                "article 14", "article 15", "article 19", "article 21", "constitutional",
                "unconstitutional", "violates article", "constitutional validity",
                "constitutional challenge", "fundamental rights", "equal protection"
            ],
            "layer": DomainLayer.BINDING_CONSTRAINTS,
            "verticals": ["judicial", "legal"]
        },
        
        # Labor domain
        "labor": {
            "keywords": [
                "appointment", "recruitment", "hiring", "employment", "contract",
                "salary", "wages", "pay scale", "allowance", "pension", "gratuity",
                "retirement", "promotion", "transfer", "disciplinary", "suspension",
                "termination", "dismissal", "service rules", "labor law", "employment law"
            ],
            "layer": DomainLayer.IMPACT_DOMAINS,
            "verticals": ["go", "legal"]
        },
        
        # Finance domain
        "finance": {
            "keywords": [
                "fee", "fees", "tuition", "charges", "payment", "budget", "allocation",
                "funding", "grant", "subsidy", "financial", "cost", "expenditure",
                "revenue", "tax", "levy", "financial commitment", "budget head"
            ],
            "layer": DomainLayer.IMPACT_DOMAINS,
            "verticals": ["go", "legal", "data"]
        },
        
        # Social justice domain
        "social_justice": {
            "keywords": [
                "minority", "minorities", "backward class", "sc", "st", "obc",
                "reservation", "quota", "affirmative action", "social justice",
                "equity", "inclusion", "access", "disadvantaged"
            ],
            "layer": DomainLayer.IMPACT_DOMAINS,
            "verticals": ["go", "legal", "judicial"]
        },
        
        # Administrative law domain
        "administrative": {
            "keywords": [
                "administrative", "delegation", "administrative action", "quasi-judicial",
                "administrative tribunal", "administrative law", "natural justice",
                "procedural fairness", "administrative decision"
            ],
            "layer": DomainLayer.BINDING_CONSTRAINTS,
            "verticals": ["judicial", "legal"]
        },
        
        # Federalism domain
        "federalism": {
            "keywords": [
                "state", "central", "union", "federal", "concurrent list", "state list",
                "union list", "jurisdiction", "jurisdictional", "state vs central",
                "federal structure", "concurrent power", "state power"
            ],
            "layer": DomainLayer.BINDING_CONSTRAINTS,
            "verticals": ["judicial", "legal", "go"]
        },
        
        # Consumer law domain
        "consumer": {
            "keywords": [
                "consumer", "unfair practice", "consumer protection", "consumer rights",
                "refund", "compensation", "deficiency in service", "consumer forum"
            ],
            "layer": DomainLayer.IMPACT_DOMAINS,
            "verticals": ["judicial", "legal"]
        },
        
        # Education domain (primary)
        "education": {
            "keywords": [
                "education", "university", "college", "school", "curriculum", "syllabus",
                "examination", "degree", "diploma", "admission", "enrollment",
                "ugc", "aicte", "naac", "nep", "autonomy", "affiliation"
            ],
            "layer": DomainLayer.PRIMARY,
            "verticals": ["go", "legal", "judicial", "scheme"]
        }
    }
    
    # Query type to domain mapping
    QUERY_TYPE_DOMAIN_HINTS = {
        "risk_analysis": ["constitutional", "judicial", "administrative"],
        "judicial_constraint": ["judicial", "constitutional", "administrative"],
        "jurisdictional": ["federalism", "constitutional"],
        "comparative": ["constitutional", "administrative"]  # Often need constraints for comparison
    }
    
    def __init__(self):
        """Initialize domain detector"""
        # Compile keyword patterns for efficiency
        self.domain_patterns = {}
        for domain, config in self.DOMAIN_KEYWORDS.items():
            keywords = config["keywords"]
            # Create case-insensitive pattern
            pattern = re.compile(
                r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b',
                re.IGNORECASE
            )
            self.domain_patterns[domain] = {
                "pattern": pattern,
                "config": config
            }
    
    def detect_domains(
        self,
        query: str,
        query_type: Optional[str] = None,
        primary_domain: Optional[str] = None
    ) -> Dict[str, List[DetectedDomain]]:
        """
        Detect which domains are needed for a query.
        
        Args:
            query: User query
            query_type: Query classification type (factual, risk_analysis, etc.)
            primary_domain: Known primary domain (e.g., "education")
            
        Returns:
            Dict with:
                - primary: List of primary domains
                - binding_constraints: List of binding constraint domains
                - impact_domains: List of impact domains
                - all_domains: Combined list of all detected domains
                - verticals: List of verticals to search
        """
        query_lower = query.lower()
        detected = {
            DomainLayer.PRIMARY: [],
            DomainLayer.BINDING_CONSTRAINTS: [],
            DomainLayer.IMPACT_DOMAINS: []
        }
        
        # If primary domain is specified, add it
        if primary_domain:
            if primary_domain in self.DOMAIN_KEYWORDS:
                detected[DomainLayer.PRIMARY].append(DetectedDomain(
                    domain=primary_domain,
                    layer=DomainLayer.PRIMARY,
                    confidence=1.0,
                    trigger_keywords=[],
                    reason="Explicitly specified primary domain"
                ))
        
        # Detect domains from keywords
        for domain, pattern_info in self.domain_patterns.items():
            pattern = pattern_info["pattern"]
            config = pattern_info["config"]
            layer = config["layer"]
            
            # Skip if already added as primary
            if primary_domain == domain:
                continue
            
            # Find matches
            matches = pattern.findall(query_lower)
            if matches:
                # Calculate confidence based on number of matches
                match_count = len(matches)
                confidence = min(0.5 + (match_count * 0.15), 1.0)
                
                detected[layer].append(DetectedDomain(
                    domain=domain,
                    layer=layer,
                    confidence=confidence,
                    trigger_keywords=list(set(matches)),
                    reason=f"Detected {match_count} keyword match(es): {', '.join(set(matches)[:3])}"
                ))
        
        # Add query type hints
        if query_type and query_type in self.QUERY_TYPE_DOMAIN_HINTS:
            hint_domains = self.QUERY_TYPE_DOMAIN_HINTS[query_type]
            for hint_domain in hint_domains:
                # Check if already detected
                already_detected = any(
                    d.domain == hint_domain
                    for layer_domains in detected.values()
                    for d in layer_domains
                )
                
                if not already_detected and hint_domain in self.DOMAIN_KEYWORDS:
                    config = self.DOMAIN_KEYWORDS[hint_domain]
                    detected[config["layer"]].append(DetectedDomain(
                        domain=hint_domain,
                        layer=config["layer"],
                        confidence=0.6,  # Lower confidence for hints
                        trigger_keywords=[],
                        reason=f"Query type '{query_type}' suggests {hint_domain} domain"
                    ))
        
        # Build result
        all_domains = []
        for layer_domains in detected.values():
            all_domains.extend(layer_domains)
        
        # Collect unique verticals
        verticals = set()
        for domain_obj in all_domains:
            domain_config = self.DOMAIN_KEYWORDS.get(domain_obj.domain, {})
            domain_verticals = domain_config.get("verticals", [])
            verticals.update(domain_verticals)
        
        # If no verticals detected, default to all
        if not verticals:
            verticals = {"go", "legal", "judicial", "scheme"}
        
        return {
            "primary": detected[DomainLayer.PRIMARY],
            "binding_constraints": detected[DomainLayer.BINDING_CONSTRAINTS],
            "impact_domains": detected[DomainLayer.IMPACT_DOMAINS],
            "all_domains": all_domains,
            "verticals": sorted(list(verticals)),
            "domain_names": [d.domain for d in all_domains]
        }
    
    def get_retrieval_strategy(
        self,
        detected_domains: Dict
    ) -> Dict:
        """
        Get retrieval strategy based on detected domains.
        
        Returns:
            Dict with:
                - layer_1_verticals: Primary domain verticals (always retrieved)
                - layer_2_verticals: Binding constraint verticals (conditional)
                - layer_3_verticals: Impact domain verticals (triggered)
                - retrieval_depth: "standard" or "deep"
        """
        primary = detected_domains.get("primary", [])
        binding = detected_domains.get("binding_constraints", [])
        impact = detected_domains.get("impact_domains", [])
        
        # Layer 1: Primary domain (always)
        layer_1_verticals = set()
        for domain_obj in primary:
            domain_config = self.DOMAIN_KEYWORDS.get(domain_obj.domain, {})
            layer_1_verticals.update(domain_config.get("verticals", []))
        
        # Layer 2: Binding constraints (always if detected)
        layer_2_verticals = set()
        for domain_obj in binding:
            domain_config = self.DOMAIN_KEYWORDS.get(domain_obj.domain, {})
            layer_2_verticals.update(domain_config.get("verticals", []))
        
        # Layer 3: Impact domains (always if detected)
        layer_3_verticals = set()
        for domain_obj in impact:
            domain_config = self.DOMAIN_KEYWORDS.get(domain_obj.domain, {})
            layer_3_verticals.update(domain_config.get("verticals", []))
        
        # Determine retrieval depth
        total_domains = len(primary) + len(binding) + len(impact)
        retrieval_depth = "deep" if total_domains > 2 else "standard"
        
        # If no domains detected, default to all verticals
        if not layer_1_verticals and not layer_2_verticals and not layer_3_verticals:
            layer_1_verticals = {"go", "legal", "judicial", "scheme"}
        
        return {
            "layer_1_verticals": sorted(list(layer_1_verticals)),
            "layer_2_verticals": sorted(list(layer_2_verticals)),
            "layer_3_verticals": sorted(list(layer_3_verticals)),
            "all_verticals": sorted(list(layer_1_verticals | layer_2_verticals | layer_3_verticals)),
            "retrieval_depth": retrieval_depth,
            "has_binding_constraints": len(binding) > 0,
            "has_impact_domains": len(impact) > 0
        }

