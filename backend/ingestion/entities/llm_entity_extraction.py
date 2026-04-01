"""
LLM Entity Extractor
Uses Gemini to extract complex entities that regex might miss
Only used for important documents in go/legal/judicial verticals
"""
import os
import json
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime
import google.auth
from google.oauth2 import service_account
from google import genai as genai_new

logger = logging.getLogger(__name__)


class InvalidContractError(Exception):
    """Raised when LLM response violates strict schema contract"""
    pass


class LLMEntityExtractor:
    """
    LLM-powered entity extractor using Gemini
    
    Purpose:
    - Catch entities that regex patterns miss
    - Extract context-dependent entities
    - Improve entity quality for critical documents
    
    Philosophy:
    - Use sparingly (expensive and slow)
    - Only for documents where regex finds few entities
    - Complement, don't replace regex
    """
    
    # Strict enums for validation
    VALID_ARCHETYPES = {"normative", "administrative", "financial", "procedural"}
    VALID_ACTIONS = {"amends", "supersedes", "cancels", "clarifies", "references"}
    VALID_DATE_ROLES = {"issue_date", "effective_from", "retrospective_from", "reference_date"}
    VALID_CLAUSE_TYPES = {"rule", "exception", "procedure", "explanation"}
    
    # Fields to NEVER output (interpretive/policy-judgment fields)
    FORBIDDEN_FIELDS = {
        "go_effect", "legal_effect", "authority_level", 
        "applicability_scope", "years", "effective_until"
    }
    
    def __init__(self, project_id: str = None, location: str = "asia-south1", model_name: str = "gemini-2.5-flash"):
        """
        Initialize LLM extractor using Vertex AI (OAuth)
        """
        self.model_name = model_name
        self.location = location
        self.enabled = False
        
        # Resolve Project ID
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        
        try:
            # Get credentials
            service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if service_account_file and os.path.exists(service_account_file):
                scopes = ['https://www.googleapis.com/auth/cloud-platform']
                creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)
                
                if not self.project_id:
                    with open(service_account_file, 'r') as f:
                        self.project_id = json.load(f).get('project_id')
            else:
                creds, computed_project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
                self.project_id = self.project_id or computed_project
            
            if self.project_id:
                self.client = genai_new.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location,
                    credentials=creds,
                )
                self.enabled = True
                logger.info(f"✅ Vertex AI initialized: {self.model_name}")
            else:
                logger.warning("GOOGLE_CLOUD_PROJECT_ID not found - Disabling LLM")
                
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI Client: {e}")
            self.enabled = False
    
    def extract(
        self, 
        text: str, 
        vertical: str, 
        doc_id: str = ""
    ) -> Dict[str, List[str]]:
        """
        Extract entities using LLM
        
        Args:
            text: Document text
            vertical: Document vertical
            doc_id: Document ID
            
        Returns:
            Dictionary of entity types and values
        """
        if not self.enabled:
            return {}
        
        if not text or len(text) < 500:
            return {}
        
        try:
            # Truncate if too long
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            # Build prompt
            prompt = self._build_prompt(text, vertical)
            
            # Call Gemini via Vertex AI
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai_new.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            # Parse response
            entities = self._parse_response(response.text)
            
            logger.info(f"LLM extracted {sum(len(v) for v in entities.values())} entities from {doc_id}")
            
            return entities
            
        except Exception as e:
            logger.error(f"LLM entity extraction failed for {doc_id}: {e}")
            return {}
    
    def extract_go_legal_context(
        self,
        text: str,
        doc_id: str = ""
    ) -> Dict:
        """
        Extract GO legal context using LLM
        Focus on legal effect and dependencies, not entity lists
        
        Args:
            text: GO document text
            doc_id: Document ID
            
        Returns:
            Dictionary with legal context (go_archetype, legal_actions, dates, etc.)
        """
        if not self.enabled:
            return {}
        
        if not text or len(text) < 500:
            return {}
        
        try:
            # Truncate if too long
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            # Build GO-specific prompt
            prompt = self._build_go_legal_prompt(text)
            
            # Call Gemini via Vertex AI
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai_new.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            # Parse GO legal context
            context = self._parse_go_legal_response(response.text)
            
            # Validate output contract
            self._validate_output_contract(context)
            
            logger.info(f"LLM extracted GO legal context from {doc_id}: {context.get('go_archetype', 'unknown')}")
            
            return context
            
        except InvalidContractError as e:
            logger.error(f"Contract violation in {doc_id}: {e}")
            return {}
        except Exception as e:
            logger.error(f"LLM GO legal context extraction failed for {doc_id}: {e}")
            return {}
    
    def _build_prompt(self, text: str, vertical: str) -> str:
        """Build extraction prompt based on vertical"""
        
        # For GO vertical, use legal context extraction instead
        if vertical == "go":
            return self._build_go_legal_prompt(text)
        
        if vertical == "legal":
            entity_types = """
1. ACT_NAMES - Act names (e.g., Right to Education Act, 2009)
2. SECTIONS - Section numbers and references
3. RULES - Rule references
4. AMENDMENTS - Amendment references
5. DATES - Enactment/amendment dates
6. AUTHORITIES - Implementing authorities
"""
        elif vertical == "judicial":
            entity_types = """
1. CASE_NUMBERS - Case/petition numbers
2. PARTIES - Petitioner/Respondent names
3. COURTS - Court names
4. JUDGES - Judge names
5. ACTS_CITED - Acts and sections cited
6. DATES - Important dates (filing, hearing, judgment)
"""
        else:
            entity_types = """
1. KEY_TERMS - Important domain-specific terms
2. ORGANIZATIONS - Organizations mentioned
3. DATES - Important dates
4. REFERENCES - Document references
"""
        
        prompt = f"""You are an expert in Indian policy documents. Extract entities from this {vertical} document.

Document text:
{text}

Extract the following entity types:
{entity_types}

Return ONLY a JSON object in this EXACT format:
{{
  "acts": ["Right to Education Act, 2009"],
  "sections": ["Section 5", "Section 12(1)"],
  "dates": ["15.08.2023", "01.04.2024"],
  "organizations": ["NCTE", "UGC"]
}}

Rules:
- Only extract entities actually present in the text
- Normalize formats
- Remove duplicates
- Limit each type to max 10 entities
- If a type has no entities, use empty array: []

JSON only, no explanation:"""
        
        return prompt
    
    def _build_go_legal_prompt(self, text: str) -> str:
        """Build GO-specific legal context extraction prompt"""
        
        prompt = f"""You are a legal analyst for Government Orders.
        
Analyze this document and extract high-precision metadata.

STRICT NEGATIVE CONSTRAINTS (Violating these poisons the system):
- DO NOT decide if the GO is active, valid, or in-force.
- DO NOT infer repeal unless explicitly stated.
- DO NOT guess missing dates.
- DO NOT normalize department names.
- DO NOT resolve GO references (just extract the string).
- DO NOT interpret legal clauses (just classify their intent).

1. GO Archetype (Mandatory - must be exactly one):
   - "normative": Creates/modifies general rules, acts, or widespread policies.
   - "administrative": Individual transfers, postings, sanctions, or limited-scope orders.
   - "financial": Pure funding release or budget approval.
   - "procedural": Meeting notices, holidays, corrigenda, or routine circulars.
   
2. Legal Actions (What this GO *does*):
   - "amends": Changes specific words/clauses in an existing GO/Act.
   - "supersedes": Completely replaces an existing GO.
   - "cancels": Revokes an existing GO.
   - "clarifies": Explains an existing GO without changing it.
   - "references": Mentions another GO without modifying it.
   
3. Beneficiary Details (Be Hyper-Specific):
   - "specific_orgs": Specific schools, colleges, or institutions named.
   - "beneficiary_types": Types of people (e.g., "Students of Class IX", "Secondary Grade Teachers").
   - "count": Number of beneficiaries if mentioned.
   
4. Geographic Scope:
   - "districts", "mandals", "villages" (Lists of specific names).
   
5. Dates with Roles (Mandatory extraction):
   - "issue_date": Date this order was signed/issued.
   - "effective_from": Date from which the order is valid.
   - "retrospective_from": If strict retrospective effect is mentioned.
   - "reference_date": Other dates used for calculation/reference.
   
6. Clause Classification (Semantic Intent):
   - Classify paragraphs/clauses into: "rule", "exception", "procedure", "explanation".
   - Provide the start text (first 10 chars) for mapping.

Document text:
{text}

Return JSON only in this EXACT format:
{{
  "go_archetype": "normative",
  "legal_actions": [
    {{ "action": "amends", "target": "G.O.Ms.No. 45" }}
  ],
  "dates": [
    {{ "value": "2023-08-15", "role": "issue_date" }},
    {{ "value": "2023-06-01", "role": "retrospective_from" }}
  ],
  "policy_domain": "School Infrastructure",
  "financial_details": {{
     "financial_commitment": false,
     "amount": null,
     "budget_head": null
  }},
  "beneficiary_details": {{
    "specific_orgs": [],
    "beneficiary_types": ["Students"],
    "count": null
  }},
  "geographic_details": {{ "districts": [], "mandals": [], "villages": [] }},
  "clause_map": [
     {{ "text_start": "The Govern", "type": "rule" }},
     {{ "text_start": "Provided t", "type": "exception" }}
  ],
  "specialized_terms": []
}}

Rules:
- Dates must be YYYY-MM-DD.
- Enums (archetype, action, role, type) are case-sensitive and strict.
- DO NOT include: go_effect, legal_effect, authority_level, applicability_scope, years

JSON only, no explanation:"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, List[str]]:
        """Parse LLM JSON response"""
        try:
            # Clean response
            response_text = response_text.strip()
            
            # Remove markdown if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            if not isinstance(data, dict):
                logger.error("LLM response is not a dict")
                return {}
            
            # Validate and clean
            entities = {}
            valid_keys = {
                "go_numbers", "sections", "rules", "dates", 
                "departments", "schemes", "acts", "case_numbers",
                "parties", "courts", "judges", "acts_cited",
                "organizations", "beneficiaries", "authorities"
            }
            
            for key, values in data.items():
                # Normalize key
                key_lower = key.lower().replace(" ", "_")
                
                # Skip if not valid key
                if key_lower not in valid_keys:
                    continue
                
                # Validate values
                if isinstance(values, list):
                    # Clean values
                    cleaned_values = []
                    for v in values[:10]:  # Limit to 10
                        if isinstance(v, str) and v.strip():
                            cleaned_values.append(v.strip())
                    
                    if cleaned_values:
                        entities[key_lower] = cleaned_values
            
            return entities
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            logger.debug(f"Response text: {response_text[:200]}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {}
    
    def _parse_go_legal_response(self, response_text: str) -> Dict:
        """Parse GO legal context JSON response"""
        try:
            # Clean response
            response_text = response_text.strip()
            
            # Remove markdown if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            if not isinstance(data, dict):
                logger.error("LLM GO legal response is not a dict")
                return {}
            
            # Validate and structure
            context = {}
            
            # 1. Archetype (Strict Enum) - REQUIRED - MUST BE STRING
            if "go_archetype" not in data:
                raise InvalidContractError("Missing mandatory field: go_archetype")
            
            archetype = str(data["go_archetype"]).lower()
            
            # Coerce variations to valid archetypes
            archetype_mapping = {
                "normative_policy": "normative",
                "normative": "normative",
                "administrative_action": "administrative",
                "administrative": "administrative",
                "financial_sanction": "financial",
                "financial": "financial",
                "procedural_notice": "procedural",
                "procedural": "procedural"
            }
            
            archetype = archetype_mapping.get(archetype)
            if archetype not in self.VALID_ARCHETYPES:
                raise InvalidContractError(f"Invalid archetype: {data['go_archetype']}")
            
            # Store as STRING, not list
            context["go_archetype"] = archetype

            # 2. Legal Actions (Strict Enum for action)
            if "legal_actions" in data and isinstance(data["legal_actions"], list):
                clean_actions = []
                for item in data["legal_actions"]:
                    if isinstance(item, dict) and item.get("action") in self.VALID_ACTIONS:
                        clean_actions.append({
                            "action": item["action"],
                            "target": str(item.get("target", ""))
                        })
                if clean_actions:
                    context["legal_actions"] = clean_actions
            
            # Normative archetype MUST have actions
            if context["go_archetype"] == "normative" and not context.get("legal_actions"):
                raise InvalidContractError("Normative policy must have at least one legal action")

            # 3. Dates (Strict Roles) - STRUCTURED ONLY
            if "dates" in data and isinstance(data["dates"], list):
                clean_dates = []
                seen_roles = set()
                
                for item in data["dates"]:
                    if isinstance(item, dict) and item.get("role") in self.VALID_DATE_ROLES:
                        role = item["role"]
                        
                        # Skip duplicate roles instead of failing
                        if role in seen_roles:
                            logger.warning(f"Skipping duplicate date role: {role} in {doc_id}")
                            continue
                        
                        # Normalize date to YYYY-MM-DD
                        date_value = item.get("value", "")
                        normalized_date = self._normalize_date(date_value)
                        
                        if normalized_date:
                            seen_roles.add(role)
                            clean_dates.append({
                                "value": normalized_date,
                                "role": role
                            })
                
                if clean_dates:
                    context["dates"] = clean_dates

            # 4. Clause Map (Strict Types) - Lightweight extraction only
            if "clause_map" in data and isinstance(data["clause_map"], list):
                clean_clauses = []
                for item in data["clause_map"]:
                    if isinstance(item, dict) and item.get("type") in self.VALID_CLAUSE_TYPES:
                        clean_clauses.append({
                            "text_start": str(item.get("text_start", ""))[:50],  # Limit length
                            "type": item["type"]
                        })
                if clean_clauses:
                    context["clause_map"] = clean_clauses
            
            # 5. Financial Details
            if "financial_details" in data and isinstance(data["financial_details"], dict):
                fd = data["financial_details"]
                if "financial_commitment" in fd:
                    context["financial_commitment"] = [str(fd["financial_commitment"]).lower()]
                if "amount" in fd and fd["amount"]:
                    context["financial_amount"] = [str(fd["amount"])]
                if "budget_head" in fd and fd["budget_head"]:
                    context["budget_head"] = [str(fd["budget_head"])]
                    
            # 6. Beneficiary Details (NO mixing with departments)
            if "beneficiary_details" in data and isinstance(data["beneficiary_details"], dict):
                bd = data["beneficiary_details"]
                if "specific_orgs" in bd and isinstance(bd["specific_orgs"], list):
                    clean_orgs = [str(o) for o in bd["specific_orgs"] if o]
                    if clean_orgs:
                        context["beneficiary_orgs"] = clean_orgs
                if "beneficiary_types" in bd and isinstance(bd["beneficiary_types"], list):
                    clean_types = [str(t) for t in bd["beneficiary_types"] if t]
                    if clean_types:
                        context["beneficiary_types"] = clean_types
                if "count" in bd and bd["count"]:
                    context["beneficiary_count"] = [str(bd["count"])]
                    
            # 7. Geographic Details
            if "geographic_details" in data and isinstance(data["geographic_details"], dict):
                gd = data["geographic_details"]
                if "districts" in gd and isinstance(gd["districts"], list):
                    clean_districts = [str(d) for d in gd["districts"] if d]
                    if clean_districts:
                        context["districts"] = clean_districts
                if "mandals" in gd and isinstance(gd["mandals"], list):
                    clean_mandals = [str(m) for m in gd["mandals"] if m]
                    if clean_mandals:
                        context["mandals"] = clean_mandals
                if "villages" in gd and isinstance(gd["villages"], list):
                    clean_villages = [str(v) for v in gd["villages"] if v]
                    if clean_villages:
                        context["villages"] = clean_villages
            
            # 8. Policy Domain
            if "policy_domain" in data:
                context["policy_domain"] = [str(data["policy_domain"])]
                
            # 9. Specialized Terms
            if "specialized_terms" in data and isinstance(data["specialized_terms"], list):
                clean_terms = [str(t) for t in data["specialized_terms"] if t]
                if clean_terms:
                    context["specialized_terms"] = clean_terms

            return context
            
        except InvalidContractError:
            # Re-raise contract violations for strict enforcement
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GO legal JSON: {e}")
            logger.debug(f"Response text: {response_text[:200]}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing GO legal response: {e}")
            return {}
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normalize date to YYYY-MM-DD format
        Returns None if normalization fails
        """
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Already in correct format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        # Common Indian formats
        date_patterns = [
            (r'(\d{2})[./](\d{2})[./](\d{4})', lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)}"),  # DD.MM.YYYY
            (r'(\d{4})[./](\d{2})[./](\d{2})', lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),  # YYYY.MM.DD
            (r'(\d{1,2})[./](\d{1,2})[./](\d{4})', lambda m: f"{m.group(3)}-{m.group(2):0>2}-{m.group(1):0>2}"),  # D.M.YYYY
        ]
        
        for pattern, formatter in date_patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    normalized = formatter(match)
                    # Validate the date
                    datetime.strptime(normalized, '%Y-%m-%d')
                    return normalized
                except (ValueError, AttributeError):
                    continue
        
        # If all patterns fail, return None
        logger.warning(f"Failed to normalize date: {date_str}")
        return None
    
    def _validate_output_contract(self, context: Dict) -> None:
        """
        Validate output contract before returning
        Fail fast if contract is violated
        """
        # Check for forbidden fields
        forbidden_found = set(context.keys()) & self.FORBIDDEN_FIELDS
        if forbidden_found:
            raise InvalidContractError(f"Forbidden fields in output: {forbidden_found}")
        
        # go_archetype must be a string, not a list
        if "go_archetype" in context:
            if not isinstance(context["go_archetype"], str):
                raise InvalidContractError(f"go_archetype must be string, got: {type(context['go_archetype'])}")
            if context["go_archetype"] not in self.VALID_ARCHETYPES:
                raise InvalidContractError(f"Invalid go_archetype value: {context['go_archetype']}")
        
        # Dates must be structured only
        if "dates" in context:
            if not isinstance(context["dates"], list):
                raise InvalidContractError("dates must be a list")
            for date_item in context["dates"]:
                if not isinstance(date_item, dict):
                    raise InvalidContractError(f"Date must be dict, got: {type(date_item)}")
                if "value" not in date_item or "role" not in date_item:
                    raise InvalidContractError(f"Date missing required fields: {date_item}")
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_item["value"]):
                    raise InvalidContractError(f"Date not in YYYY-MM-DD format: {date_item['value']}")
                if date_item["role"] not in self.VALID_DATE_ROLES:
                    raise InvalidContractError(f"Invalid date role: {date_item['role']}")
        
        logger.info("✅ Output contract validated successfully")


def create_llm_entity_extractor() -> Optional[LLMEntityExtractor]:
    """
    Factory function to create LLM entity extractor
    
    Returns:
        LLMEntityExtractor instance or None if failed
    """
    try:
        extractor = LLMEntityExtractor()
        return extractor if extractor.enabled else None
    except Exception as e:
        logger.error(f"Failed to create LLM entity extractor: {e}")
        return None