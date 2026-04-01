"""
GO Chain Builder
Builds lineage graphs between Government Orders using extracted relations.
Computes derived fields like is_superseded, is_most_recent, and traces full lineages.
"""
import logging
from typing import Dict, List, Optional, Set, Any
from collections import deque

logger = logging.getLogger(__name__)

class GOChainBuilder:
    """
    Builds and manages the graph of GO relations.
    Handles cross-document lineage tracking.
    """
    
    def __init__(self):
        # Map: go_number -> metadata
        self.nodes = {}
        # Directed Edges: source_go -> list of targets it relates to
        self.adj = {}
        # Reverse Edges: target_go -> list of sources relating to it
        self.rev_adj = {}
        
    def add_go(self, go_number: str, metadata: Dict[str, Any], relations: List[Dict[str, Any]]):
        """
        Adds a GO and its relations to the builder.
        
        Args:
            go_number: Canonical GO number (e.g., G.O.MS.No.45)
            metadata: Basic metadata (year, doc_id, etc.)
            relations: List of relation dicts as extracted by GORelationExtractor
        """
        if not go_number:
            return
            
        self.nodes[go_number] = {
            "metadata": metadata,
            "relations": relations
        }
        
        if go_number not in self.adj:
            self.adj[go_number] = []
        
        for rel in relations:
            target = rel.get("target_go")
            if not target:
                continue
                
            # source -> target
            self.adj[go_number].append(rel)
            
            # reverse: target -> source
            if target not in self.rev_adj:
                self.rev_adj[target] = []
            self.rev_adj[target].append({
                "source_go": go_number,
                "relation_type": rel["relation_type"]
            })

    def build_chains(self) -> Dict[str, Dict[str, Any]]:
        """
        Computes derived fields for all registered GOs.
        
        Returns:
            Map: go_number -> derived_metadata
        """
        results = {}
        
        for go_number in self.nodes:
            # Derived fields
            is_superseded = False
            superseded_by = None
            is_most_recent = True
            
            # Check if anyone supersedes THIS go
            # Look at reverse adjacency for "supersedes" or "amends" (if partial replacement is treated as newer version)
            if go_number in self.rev_adj:
                for incoming in self.rev_adj[go_number]:
                    if incoming["relation_type"] in ["supersedes", "amends"]:
                        # This GO is pointed to by a newer GO
                        is_superseded = True
                        is_most_recent = False
                        superseded_by = incoming["source_go"]
                        break # Simplification: first one found. In reality, could be multiple.
            
            results[go_number] = {
                "is_superseded": is_superseded,
                "superseded_by": superseded_by,
                "is_most_recent": is_most_recent,
                "overrides_by_date": False
            }

            # NEW: Temporal Precedence Logic (Refinement 2)
            # If not already superseded by relation, check for date-based overlaps 
            # in the same subject/department.
            if not is_superseded:
                newer_go = self._find_newer_go_on_same_topic(go_number)
                if newer_go:
                    results[go_number]["is_superseded"] = True
                    results[go_number]["superseded_by"] = newer_go
                    results[go_number]["is_most_recent"] = False
                    results[go_number]["overrides_by_date"] = True
            
        return results

    def _find_newer_go_on_same_topic(self, go_num: str) -> Optional[str]:
        """Finds if there's a newer GO with high overlap in subject/dept"""
        curr_node = self.nodes[go_num]
        curr_meta = curr_node.get("metadata", {})
        curr_date = curr_meta.get("effective_date") or curr_meta.get("date_issued")
        curr_dept = curr_meta.get("department")
        curr_subject = curr_meta.get("subject", "").lower()
        
        if not curr_date:
            return None
            
        for target_go, target_node in self.nodes.items():
            if target_go == go_num: continue
            
            target_meta = target_node.get("metadata", {})
            target_date = target_meta.get("effective_date") or target_meta.get("date_issued")
            target_dept = target_meta.get("department")
            target_subject = target_meta.get("subject", "").lower()
            
            if not target_date or target_dept != curr_dept:
                continue
                
            # If target is newer
            if target_date > curr_date:
                # Simple subject overlap check (token-based or domain-based)
                # If they share critical keywords/domains, target likely supercedes curr
                common_tokens = set(curr_subject.split()) & set(target_subject.split())
                # Filter out short/common words
                meaningful_common = [t for t in common_tokens if len(t) > 4]
                
                # Loosened threshold: 2 tokens is enough for common policy topics (Change 2)
                if len(meaningful_common) >= 2:
                    return target_go
        
        return None

    def trace_lineage(self, go_number: str) -> List[str]:
        """
        Traces the full chain of a GO up to the most recent or down to the original.
        For now, returns a list of GO numbers in chronological order (oldest to newest).
        """
        if go_number not in self.nodes and go_number not in self.rev_adj:
            return [go_number] if go_number else []

        # Find the root (oldest) by following targets recursively
        def find_root(curr):
            # Check outgoing relations for something it supersedes
            if curr in self.adj:
                for rel in self.adj[curr]:
                    if rel["relation_type"] in ["supersedes", "amends"]:
                        return find_root(rel["target_go"])
            return curr

        # Find the leaf (newest) by following reverse adj recursively
        def find_leaf(curr):
            if curr in self.rev_adj:
                for incoming in self.rev_adj[curr]:
                    if incoming["relation_type"] in ["supersedes", "amends"]:
                        return find_leaf(incoming["source_go"])
            return curr

        # For the sake of this implementation, let's just build the path from root to leaf
        root = find_root(go_number)
        
        chain = []
        curr = root
        visited = set()
        
        while curr and curr not in visited:
            visited.add(curr)
            chain.append(curr)
            next_go = None
            if curr in self.rev_adj:
                for incoming in self.rev_adj[curr]:
                    if incoming["relation_type"] in ["supersedes", "amends"]:
                        next_go = incoming["source_go"]
                        break
            curr = next_go
            
        return chain

    def validate_graph(self) -> List[str]:
        """Detects cycles in the GO relations."""
        errors = []
        visited = set()
        path = set()

        def visit(u):
            if u in path:
                return True
            if u in visited:
                return False
            
            visited.add(u)
            path.add(u)
            
            if u in self.adj:
                for rel in self.adj[u]:
                    v = rel["target_go"]
                    if v and visit(v):
                        return True
            
            path.remove(u)
            return False

        for node in list(self.nodes.keys()):
            if node not in visited:
                if visit(node):
                    errors.append(f"Cycle detected involving {node}")
        
        return errors
