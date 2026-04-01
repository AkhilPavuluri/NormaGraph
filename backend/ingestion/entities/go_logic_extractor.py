"""
GO Logic Extractor
Deterministic rule-based extraction of GO-critical entities
Fast, reliable, and specific to Government Order semantics
"""
import re
import logging
from typing import Dict, List, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class GOLogicExtractor:
    """
    Extract GO-specific logical entities using deterministic rules
    
    Extracts:
    - go_effect: What this GO does (supersession, amendment, cancellation, etc.)
    - applicability_scope: Geographic/institutional scope
    - legal_effect: Enforceable vs advisory
    - authority_level: Decision-making level
    - beneficiary_scope: Who it applies to
    - financial_impact: Budget vs policy-only
    """
    
    def __init__(self):
        """Initialize GO logic patterns"""
        
        # GO Effect patterns - More comprehensive
        self.supersession_patterns = [
            re.compile(r'\bsupersede[sd]?\b', re.IGNORECASE),
            re.compile(r'\bin\s+supersession\s+of\b', re.IGNORECASE),
            re.compile(r'\breplaces?\b.*\bG\.?O\.?\b', re.IGNORECASE),
            re.compile(r'\bin\s+place\s+of\b.*\bG\.?O\.?\b', re.IGNORECASE),
            re.compile(r'\bstand[s]?\s+superseded\b', re.IGNORECASE),
        ]
        
        self.amendment_patterns = [
            re.compile(r'\bamend[sment]*\b', re.IGNORECASE),
            re.compile(r'\bin\s+(?:partial\s+)?modification\s+of\b', re.IGNORECASE),
            re.compile(r'\bmodif(?:y|ies|ied)\b', re.IGNORECASE),
            re.compile(r'\brevise[sd]?\b', re.IGNORECASE),
            re.compile(r'\bsubstitute[sd]?\b', re.IGNORECASE),
        ]
        
        self.cancellation_patterns = [
            re.compile(r'\bcancel[slation]*\b', re.IGNORECASE),
            re.compile(r'\brescind[sed]?\b', re.IGNORECASE),
            re.compile(r'\bwithdr[aw|awn]\b', re.IGNORECASE),
            re.compile(r'\bnull\s+and\s+void\b', re.IGNORECASE),
        ]
        
        self.clarification_patterns = [
            re.compile(r'\bclarif(?:y|ies|ied|ication)\b', re.IGNORECASE),
            re.compile(r'\bfor\s+clarification\b', re.IGNORECASE),
            re.compile(r'\bto\s+clarify\b', re.IGNORECASE),
            re.compile(r'\bexplanation\b', re.IGNORECASE),
        ]
        
        # Applicability scope patterns - More comprehensive
        self.statewide_patterns = [
            re.compile(r'\ball\s+districts?\b', re.IGNORECASE),
            re.compile(r'\bstate\s*wide\b', re.IGNORECASE),
            re.compile(r'\bthroughout\s+(?:the\s+)?state\b', re.IGNORECASE),
            re.compile(r'\ball\s+government\s+(?:schools?|institutions?)\b', re.IGNORECASE),
            re.compile(r'\bentire\s+state\b', re.IGNORECASE),
            re.compile(r'\bacross\s+the\s+state\b', re.IGNORECASE),
            re.compile(r'\bin\s+the\s+state\b', re.IGNORECASE),
        ]
        
        self.regional_patterns = [
            re.compile(r'\b(?:municipal|mandal|district|zone|division)\b', re.IGNORECASE),
            re.compile(r'\bspecific\s+districts?\b', re.IGNORECASE),
            re.compile(r'\bin\s+the\s+district\s+of\b', re.IGNORECASE),
            re.compile(r'\bselected\s+(?:districts?|areas?)\b', re.IGNORECASE),
        ]
        
        self.institutional_patterns = [
            re.compile(r'\bspecific\s+(?:school|college|institution)s?\b', re.IGNORECASE),
            re.compile(r'\bnamed\s+institution\b', re.IGNORECASE),
            re.compile(r'\bfollowing\s+(?:schools?|institutions?)\b', re.IGNORECASE),
        ]
        
        # Legal effect patterns - More comprehensive
        self.enforceable_patterns = [
            re.compile(r'\b(?:shall|must|mandatory|compulsory|required)\b', re.IGNORECASE),
            re.compile(r'\bwith\s+immediate\s+effect\b', re.IGNORECASE),
            re.compile(r'\bstrictly\s+(?:follow|adhere|comply)\b', re.IGNORECASE),
            re.compile(r'\bordered\s+to\b', re.IGNORECASE),
            re.compile(r'\bdirected\s+to\b', re.IGNORECASE),
            re.compile(r'\bhereby\s+(?:ordered|directed)\b', re.IGNORECASE),
        ]
        
        self.advisory_patterns = [
            re.compile(r'\b(?:may|should|recommend|suggest|advise)\b', re.IGNORECASE),
            re.compile(r'\bguidance\b', re.IGNORECASE),
            re.compile(r'\bfor\s+consideration\b', re.IGNORECASE),
            re.compile(r'\bvoluntary\b', re.IGNORECASE),
        ]
        
        # Authority level patterns
        self.cabinet_patterns = [
            re.compile(r'\bcabinet\b', re.IGNORECASE),
            re.compile(r'\bcouncil\s+of\s+ministers\b', re.IGNORECASE),
            re.compile(r'\bchief\s+minister\b', re.IGNORECASE),
        ]
        
        self.secretary_patterns = [
            re.compile(r'\b(?:principal\s+)?secretary\b', re.IGNORECASE),
            re.compile(r'\bsecretary\s+to\s+government\b', re.IGNORECASE),
        ]
        
        self.director_patterns = [
            re.compile(r'\bdirector(?:ate)?\b', re.IGNORECASE),
            re.compile(r'\bcommissioner\b', re.IGNORECASE),
        ]
        
        # Beneficiary scope patterns - More comprehensive
        self.teacher_patterns = [
            re.compile(r'\bteachers?\b', re.IGNORECASE),
            re.compile(r'\bteaching\s+staff\b', re.IGNORECASE),
            re.compile(r'\bfaculty\b', re.IGNORECASE),
            re.compile(r'\beducators?\b', re.IGNORECASE),
            re.compile(r'\blecturers?\b', re.IGNORECASE),
            re.compile(r'\bprofessors?\b', re.IGNORECASE),
        ]
        
        self.student_patterns = [
            re.compile(r'\bstudents?\b', re.IGNORECASE),
            re.compile(r'\bpupils?\b', re.IGNORECASE),
            re.compile(r'\blearners?\b', re.IGNORECASE),
            re.compile(r'\bchildren\b', re.IGNORECASE),
            re.compile(r'\bbeneficiaries\b', re.IGNORECASE),
        ]
        
        self.officer_patterns = [
            re.compile(r'\bofficers?\b', re.IGNORECASE),
            re.compile(r'\badministrative\s+staff\b', re.IGNORECASE),
            re.compile(r'\bnon-teaching\s+staff\b', re.IGNORECASE),
            re.compile(r'\bemployees?\b', re.IGNORECASE),
            re.compile(r'\bofficials?\b', re.IGNORECASE),
        ]
        
        self.institution_patterns = [
            re.compile(r'\b(?:schools?|colleges?|institutions?)\b', re.IGNORECASE),
            re.compile(r'\beducational\s+institutions?\b', re.IGNORECASE),
            re.compile(r'\buniversities\b', re.IGNORECASE),
        ]
        
        # Financial impact patterns - More comprehensive
        self.budget_patterns = [
            re.compile(r'\b(?:budget|fund|allocation|expenditure|grant)\b', re.IGNORECASE),
            re.compile(r'\b(?:Rs\.?|rupees|crores?|lakhs?|thousands?)\b', re.IGNORECASE),
            re.compile(r'\bfinancial\s+(?:assistance|support|aid|provision)\b', re.IGNORECASE),
            re.compile(r'\bsanction(?:ed)?\s+(?:amount|fund)\b', re.IGNORECASE),
            re.compile(r'\b(?:payment|salary|stipend|scholarship)\b', re.IGNORECASE),
            re.compile(r'\b(?:₹|INR)\s*\d+\b', re.IGNORECASE),
        ]
        
        logger.info("GO Logic Extractor initialized")
    
    def extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extract GO-critical entities from text
        
        Args:
            text: GO document text
            
        Returns:
            Dictionary of GO-critical entities
        """
        if not text or not text.strip():
            return {}
        
        entities = {}
        
        # Extract GO effects
        go_effects = self._extract_go_effects(text)
        if go_effects:
            entities["go_effect"] = go_effects
        
        # Extract applicability scope
        applicability = self._extract_applicability_scope(text)
        if applicability:
            entities["applicability_scope"] = applicability
        
        # Extract legal effect
        legal_effect = self._extract_legal_effect(text)
        if legal_effect:
            entities["legal_effect"] = legal_effect
        
        # Extract authority level
        authority = self._extract_authority_level(text)
        if authority:
            entities["authority_level"] = authority
        
        # Extract beneficiary scope
        beneficiaries = self._extract_beneficiary_scope(text)
        if beneficiaries:
            entities["beneficiary_scope"] = beneficiaries
        
        # Extract financial impact
        financial = self._extract_financial_impact(text)
        if financial:
            entities["financial_impact"] = financial
        
        return entities
    
    def _extract_go_effects(self, text: str) -> List[str]:
        """Extract what this GO does (supersede, amend, cancel, clarify, issue)"""
        effects = []
        
        # Check for supersession
        if any(pattern.search(text) for pattern in self.supersession_patterns):
            effects.append("supersession")
        
        # Check for amendment
        if any(pattern.search(text) for pattern in self.amendment_patterns):
            effects.append("amendment")
        
        # Check for cancellation
        if any(pattern.search(text) for pattern in self.cancellation_patterns):
            effects.append("cancellation")
        
        # Check for clarification
        if any(pattern.search(text) for pattern in self.clarification_patterns):
            effects.append("clarification")
        
        # If no specific effect found, assume issuance
        if not effects:
            effects.append("issuance")
        
        return effects
    
    def _extract_applicability_scope(self, text: str) -> List[str]:
        """Extract geographic/institutional scope"""
        scopes = []
        
        # Check for statewide
        if any(pattern.search(text) for pattern in self.statewide_patterns):
            scopes.append("statewide")
        
        # Check for regional
        if any(pattern.search(text) for pattern in self.regional_patterns):
            scopes.append("regional")
        
        # Check for institutional
        if any(pattern.search(text) for pattern in self.institutional_patterns):
            scopes.append("institutional")
        
        # Default to statewide if not specified
        if not scopes:
            scopes.append("statewide")
        
        return scopes
    
    def _extract_legal_effect(self, text: str) -> List[str]:
        """Extract whether enforceable or advisory"""
        effects = []
        
        # Check for enforceable
        if any(pattern.search(text) for pattern in self.enforceable_patterns):
            effects.append("enforceable")
        
        # Check for advisory
        if any(pattern.search(text) for pattern in self.advisory_patterns):
            effects.append("advisory")
        
        # Default to enforceable (GOs are typically mandatory)
        if not effects:
            effects.append("enforceable")
        
        return effects
    
    def _extract_authority_level(self, text: str) -> List[str]:
        """Extract decision-making authority level"""
        levels = []
        
        # Check for cabinet level
        if any(pattern.search(text) for pattern in self.cabinet_patterns):
            levels.append("cabinet")
        
        # Check for secretary level
        if any(pattern.search(text) for pattern in self.secretary_patterns):
            levels.append("secretary")
        
        # Check for director level
        if any(pattern.search(text) for pattern in self.director_patterns):
            levels.append("director")
        
        return levels
    
    def _extract_beneficiary_scope(self, text: str) -> List[str]:
        """Extract who the GO applies to"""
        beneficiaries = []
        
        # Check for teachers
        if any(pattern.search(text) for pattern in self.teacher_patterns):
            beneficiaries.append("teachers")
        
        # Check for students
        if any(pattern.search(text) for pattern in self.student_patterns):
            beneficiaries.append("students")
        
        # Check for officers
        if any(pattern.search(text) for pattern in self.officer_patterns):
            beneficiaries.append("officers")
        
        # Check for institutions
        if any(pattern.search(text) for pattern in self.institution_patterns):
            beneficiaries.append("institutions")
        
        return beneficiaries
    
    def _extract_financial_impact(self, text: str) -> List[str]:
        """Extract whether GO has budget implications"""
        impact = []
        
        # Check for budget-related content
        if any(pattern.search(text) for pattern in self.budget_patterns):
            impact.append("budget")
        else:
            impact.append("policy")
        
        return impact
