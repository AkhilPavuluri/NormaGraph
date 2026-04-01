
import os
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def aggregate_specialized_terms(output_root: str, target_file: str):
    """
    Scans the output directory for entities.json files and aggregates 
    specialized_terms into a single thesaurus.
    """
    thesaurus = {}
    output_path = Path(output_root)
    
    if not output_path.exists():
        logger.error(f"Output directory {output_root} does not exist.")
        return

    # Scan for entities.json files
    for entities_file in output_path.glob("**/entities.json"):
        try:
            with open(entities_file, 'r') as f:
                data = json.load(f)
                terms = data.get("specialized_terms", [])
                
                for term_entry in terms:
                    # Terms are often "ACRONYM: Definition"
                    if ":" in term_entry:
                        acronym, definition = term_entry.split(":", 1)
                        acronym = acronym.strip().upper()
                        definition = definition.strip()
                        
                        if acronym not in thesaurus:
                            thesaurus[acronym] = set()
                        thesaurus[acronym].add(definition)
                    else:
                        # Just a term
                        term = term_entry.strip().upper()
                        if term not in thesaurus:
                            thesaurus[term] = set()
        except Exception as e:
            logger.warning(f"Failed to process {entities_file}: {e}")

    # Convert sets to lists for JSON serialization
    serialized_thesaurus = {k: list(v) for k, v in thesaurus.items() if v}
    
    # Save to target file
    target_path = Path(target_file)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(target_path, 'w') as f:
        json.dump(serialized_thesaurus, f, indent=2)
    
    logger.info(f"✅ Aggregated {len(serialized_thesaurus)} terms into {target_file}")

if __name__ == "__main__":
    # Example usage
    aggregate_specialized_terms(
        "/Users/nitin/Documents/Policy-Crafter/backend/ingestion_v2/output",
        "/Users/nitin/Documents/Policy-Crafter/backend/ingestion_v2/config/ground_truth_thesaurus.json"
    )
