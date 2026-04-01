"""
Golden Query Set

Curated set of queries with known correct answers for evaluation.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass
class GoldenQuery:
    """
    A golden query with expected answer and citations.
    
    Used for evaluation to measure system accuracy.
    """
    query_id: str
    query: str
    expected_answer: str
    expected_citations: List[Dict[str, str]]  # List of {doc_id, title, authority, date}
    expected_risk_level: Optional[str] = None  # "none", "low", "medium", "high", "critical"
    query_type: Optional[str] = None  # "factual", "comparative", etc.
    domain: Optional[str] = None  # "education", "healthcare", etc.
    temporal_context: Optional[Dict] = None  # {"date": 2020, "operator": "exact"}
    notes: Optional[str] = None  # Additional context for evaluators
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "GoldenQuery":
        """Create from dictionary"""
        return cls(**data)


class GoldenQuerySet:
    """
    Collection of golden queries for evaluation.
    """
    
    def __init__(self, queries: List[GoldenQuery]):
        self.queries = queries
        self.by_id = {q.query_id: q for q in queries}
    
    def get(self, query_id: str) -> Optional[GoldenQuery]:
        """Get query by ID"""
        return self.by_id.get(query_id)
    
    def filter_by_type(self, query_type: str) -> List[GoldenQuery]:
        """Filter queries by type"""
        return [q for q in self.queries if q.query_type == query_type]
    
    def filter_by_domain(self, domain: str) -> List[GoldenQuery]:
        """Filter queries by domain"""
        return [q for q in self.queries if q.domain == domain]
    
    def save(self, filepath: Path):
        """Save golden queries to JSON file"""
        data = [q.to_dict() for q in self.queries]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, filepath: Path) -> "GoldenQuerySet":
        """Load golden queries from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        queries = [GoldenQuery.from_dict(q) for q in data]
        return cls(queries)


# Example golden queries (education domain)
EXAMPLE_GOLDEN_QUERIES = [
    GoldenQuery(
        query_id="edu_001",
        query="What did NEP 2020 say about university autonomy?",
        expected_answer="NEP 2020 emphasizes enhanced autonomy for universities, allowing them to set their own curricula and make administrative decisions.",
        expected_citations=[
            {
                "doc_id": "nep_2020",
                "title": "National Education Policy 2020",
                "authority": "Ministry of Education",
                "date": "2020"
            }
        ],
        expected_risk_level="low",
        query_type="factual",
        domain="education",
        temporal_context={"date": 2020, "operator": "exact"}
    ),
    GoldenQuery(
        query_id="edu_002",
        query="Has the Supreme Court restricted private university autonomy?",
        expected_answer="Yes, in T.M.A Pai Foundation v. State of Karnataka (2002), the Supreme Court upheld the right to establish educational institutions but allowed reasonable regulations.",
        expected_citations=[
            {
                "doc_id": "tma_pai_2002",
                "title": "T.M.A Pai Foundation v. State of Karnataka",
                "authority": "Supreme Court of India",
                "date": "2002"
            }
        ],
        expected_risk_level="none",
        query_type="judicial_constraint",
        domain="education"
    ),
    GoldenQuery(
        query_id="edu_003",
        query="Can state governments mandate admissions bypassing UGC regulations?",
        expected_answer="State governments cannot mandate admissions that bypass UGC regulations, as UGC regulations have statutory force under the UGC Act.",
        expected_citations=[
            {
                "doc_id": "ugc_act",
                "title": "University Grants Commission Act",
                "authority": "Parliament of India",
                "date": "1956"
            }
        ],
        expected_risk_level="high",
        query_type="risk_analysis",
        domain="education",
        notes="This is a high-risk scenario - state action conflicting with central statutory authority"
    ),
]


def load_golden_queries(filepath: Optional[Path] = None) -> GoldenQuerySet:
    """
    Load golden queries from file or return examples.
    
    Args:
        filepath: Path to JSON file with golden queries
        
    Returns:
        GoldenQuerySet
    """
    if filepath and Path(filepath).exists():
        return GoldenQuerySet.load(Path(filepath))
    else:
        # Return example queries
        return GoldenQuerySet(EXAMPLE_GOLDEN_QUERIES)


def create_golden_query_template(filepath: Path):
    """Create a template file for golden queries"""
    template = [
        {
            "query_id": "example_001",
            "query": "Your query here",
            "expected_answer": "Expected answer text",
            "expected_citations": [
                {
                    "doc_id": "doc_id_1",
                    "title": "Document Title",
                    "authority": "Authority Name",
                    "date": "2020"
                }
            ],
            "expected_risk_level": "low",
            "query_type": "factual",
            "domain": "education",
            "temporal_context": {"date": 2020, "operator": "exact"},
            "notes": "Additional context"
        }
    ]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"Created golden query template at {filepath}")

