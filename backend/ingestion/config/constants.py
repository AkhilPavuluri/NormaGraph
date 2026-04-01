"""
Constants and patterns for ingestion_v2 pipeline.

All regex patterns, keywords, and domain-specific constants.
"""
import re
from typing import Dict, List

# ============================================================================
# DOCUMENT TYPE PATTERNS
# ============================================================================

GO_PATTERNS = [
    r'G\.O\.(Ms|MS|Rt|RT)\.?\s*No\.?\s*\d+',
    r'GO\s+(MS|RT|Ms|Rt)\s+No\.?\s*\d+',
    r'Government\s+Order',
]

SECTION_PATTERNS = [
    r'Section\s+\d+(?:\([a-zA-Z0-9]+\))*',
    r'§\s*\d+',
    r'Sec\.\s*\d+',
]

RULE_PATTERNS = [
    r'Rule\s+\d+(?:\([a-zA-Z0-9]+\))*',
]

CLAUSE_PATTERNS = [
    r'Clause\s+\d+(?:\([a-zA-Z0-9]+\))*',
]

# ============================================================================
# ENTITY PATTERNS
# ============================================================================

# GO Numbers - multiple formats
GO_NUMBER_PATTERNS = [
    re.compile(r'G\.O\.(Ms|MS|Rt|RT)\.?\s*No\.?\s*(\d+)', re.IGNORECASE),
    re.compile(r'GO\s+(MS|RT|Ms|Rt)\s+No\.?\s*(\d+)', re.IGNORECASE),
]

# Dates - Indian formats
DATE_PATTERNS = [
    re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b'),  # DD/MM/YYYY or DD-MM-YYYY
    re.compile(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b'),  # YYYY/MM/DD
]

# Section references
SECTION_REF_PATTERNS = [
    re.compile(r'Section\s+(\d+)(?:\(([a-zA-Z0-9]+)\))*', re.IGNORECASE),
    re.compile(r'Sec\.\s*(\d+)(?:\(([a-zA-Z0-9]+)\))*', re.IGNORECASE),
]

# Department names
DEPARTMENT_KEYWORDS = [
    "Education",
    "School Education",
    "Higher Education",
    "Technical Education",
    "Finance",
    "Planning",
    "Revenue",
]

# ============================================================================
# ANDHRA PRADESH DISTRICTS
# ============================================================================

AP_DISTRICTS = [
    "Anantapur", "Chittoor", "East Godavari", "West Godavari", "Guntur",
    "Krishna", "Kurnool", "Prakasam", "Nellore", "Srikakulam",
    "Visakhapatnam", "Vizianagaram", "Kadapa", "Alluri Sitharama Raju",
    "Anakapalli", "Annamayya", "Bapatla", "Eluru", "Kakinada",
    "Konaseema", "Nandyal", "NTR", "Palnadu", "Parvathipuram Manyam",
    "Sri Potti Sriramulu Nellore", "Tirupati"
]

# ============================================================================
# EDUCATION SCHEMES
# ============================================================================

EDUCATION_SCHEMES = [
    "Jagananna Amma Vodi",
    "Jagananna Vidya Deevena",
    "Jagananna Vasathi Deevena",
    "Mid Day Meal Scheme",
    "Aarogyasri",
    "Vidya Volunteers",
    "Gorumudda",
    "Rythu Bharosa",
]

# ============================================================================
# SOCIAL CATEGORIES
# ============================================================================

SOCIAL_CATEGORIES = ["SC", "ST", "OBC", "EWS", "General", "Minority"]

# ============================================================================
# SCHOOL TYPES
# ============================================================================

SCHOOL_TYPES = [
    "Government",
    "Private",
    "Aided",
    "Residential",
    "Tribal Welfare",
    "Social Welfare",
]

# ============================================================================
# EDUCATIONAL LEVELS
# ============================================================================

EDUCATIONAL_LEVELS = [
    "Primary",
    "Upper Primary",
    "Secondary",
    "Higher Secondary",
    "High School",
    "Elementary",
]

# ============================================================================
# METRICS
# ============================================================================

EDUCATION_METRICS = [
    "GER",  # Gross Enrollment Ratio
    "NER",  # Net Enrollment Ratio
    "PTR",  # Pupil-Teacher Ratio
    "Dropout Rate",
    "Transition Rate",
    "Retention Rate",
    "Literacy Rate",
]

# ============================================================================
# RELATION KEYWORDS
# ============================================================================

RELATION_KEYWORDS = {
    "amends": [
        r"amend(?:s|ed|ing)?",
        r"modif(?:y|ies|ied|ying)",
        r"revise(?:s|d|ing)?",
        r"alter(?:s|ed|ing)?",
    ],
    "supersedes": [
        r"supersede(?:s|d|ing)?",
        r"replace(?:s|d|ing)?",
        r"substitut(?:e|es|ed|ing)",
        r"rescind(?:s|ed|ing)?",
    ],
    "governed_by": [
        r"governed by",
        r"in accordance with",
        r"as per",
        r"under",
        r"pursuant to",
    ],
    "cites": [
        r"refer(?:s|red|ring)? to",
        r"cite(?:s|d|ing)?",
        r"mention(?:s|ed|ing)?",
        r"as stated in",
    ],
}

# ============================================================================
# VERTICAL CLASSIFICATION KEYWORDS
# ============================================================================

VERTICAL_KEYWORDS = {
    "go": [
        "government order",
        "g.o.",
        "preamble",
        "order",
        "whereas",
        "now therefore",
        "annexure",
    ],
    "legal": [
        "act",
        "rule",
        "section",
        "chapter",
        "clause",
        "amendment",
        "regulation",
        "statute",
    ],
    "judicial": [
        "petitioner",
        "respondent",
        "judgment",
        "court",
        "honourable",
        "held that",
        "appeal",
        "writ",
        "case",
    ],
    "data": [
        "table",
        "figure",
        "statistics",
        "data",
        "report",
        "survey",
        "analysis",
        "enrollment",
        "percentage",
    ],
    "scheme": [
        "scheme",
        "eligibility",
        "beneficiary",
        "benefit",
        "implementation",
        "guidelines",
        "application",
        "assistance",
    ],
}

# ============================================================================
# DOCUMENT STRUCTURE MARKERS
# ============================================================================

# Government Order structure
GO_STRUCTURE_MARKERS = {
    "preamble": [r"PREAMBLE", r"WHEREAS", r"AND WHEREAS"],
    "order": [r"ORDER:", r"GOVERNMENT ORDER", r"IT IS HEREBY ORDERED"],
    "annexure": [r"ANNEXURE", r"ANNEX", r"APPENDIX"],
}

# Legal document structure
LEGAL_STRUCTURE_MARKERS = {
    "chapter": [r"CHAPTER\s+[IVX\d]+", r"Chapter\s+\d+"],
    "section": [r"Section\s+\d+", r"^\d+\."],
    "subsection": [r"\(\d+\)", r"\([a-z]\)"],
}

# Judicial document structure
JUDICIAL_STRUCTURE_MARKERS = {
    "facts": [r"FACTS", r"Background", r"Brief facts"],
    "arguments": [r"ARGUMENTS", r"Submissions", r"Contentions"],
    "judgment": [r"JUDGMENT", r"ORDER", r"HELD"],
    "ratio": [r"RATIO", r"Reasoning", r"Analysis"],
}

# ============================================================================
# TEXT CLEANING PATTERNS
# ============================================================================

# Patterns to remove
REMOVE_PATTERNS = [
    r'\[Image:.*?\]',
    r'\[Chart:.*?\]',
    r'\[Graph:.*?\]',
    r'<.*?>',  # HTML tags
    r'©|®|™',  # Copyright symbols
]

# Page markers to remove
PAGE_MARKER_PATTERNS = [
    r'\n\s*[-–—]\s*\d+\s*[-–—]\s*\n',
    r'\nPage\s+\d+\s*\n',
    r'\n\d+\s+of\s+\d+\s*\n',
    r'\n\s*[-–—]{1,}\s*Page\s+\d+\s*[-–—]{1,}\s*\n',
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def compile_patterns(pattern_list: List[str]) -> List[re.Pattern]:
    """Compile a list of regex patterns."""
    return [re.compile(p, re.IGNORECASE) for p in pattern_list]

def get_vertical_patterns() -> Dict[str, List[re.Pattern]]:
    """Get compiled patterns for vertical classification."""
    return {
        vertical: compile_patterns(keywords)
        for vertical, keywords in VERTICAL_KEYWORDS.items()
    }