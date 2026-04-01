from google.cloud import bigquery

DATASET_ID = "policy_intelligence"

# ============================================================================
# UNIFIED SCHEMA (Phase 1: Foundation)
# ============================================================================
# These tables are the single source of truth for document identity,
# authority, validity, relations, and domain classification.
# Vector DBs are derivatives, not authorities.
# ============================================================================

UNIFIED_SCHEMAS = {
    # =========================
    # 1. DOCUMENTS (Core Identity)
    # =========================
    "documents": [
        bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("doc_type", "STRING", mode="REQUIRED"),  # judgment, regulation, policy, report, go
        bigquery.SchemaField("domain", "STRING"),  # education, labor, constitution, finance, state, judicial
        bigquery.SchemaField("authority", "STRING"),  # SC, HC, UGC, State Govt, etc.
        bigquery.SchemaField("jurisdiction", "STRING"),  # AP, India, Nationwide
        bigquery.SchemaField("date", "DATE"),
        bigquery.SchemaField("version", "STRING"),  # For versioned documents
        bigquery.SchemaField("source_url", "STRING"),  # Original source URL
        bigquery.SchemaField("status", "STRING"),  # active, superseded, invalidated
        bigquery.SchemaField("raw_pdf_uri", "STRING"),  # GCS path or local path
        bigquery.SchemaField("ingested_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],

    # =========================
    # 2. JUDGMENTS_METADATA
    # =========================
    "judgments_metadata": [
        bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("court", "STRING", mode="REQUIRED"),  # Supreme Court, High Court, etc.
        bigquery.SchemaField("bench_strength", "INTEGER"),  # Number of judges
        bigquery.SchemaField("case_number", "STRING"),  # Case citation number
        bigquery.SchemaField("ratio_present", "BOOLEAN"),  # Whether ratio decidendi is identified
        bigquery.SchemaField("binding_strength", "STRING"),  # binding, persuasive, informative
        bigquery.SchemaField("petition_result", "STRING"),  # allowed, dismissed, partly_allowed
        bigquery.SchemaField("order_type", "STRING"),  # directions, quashed, upheld, remanded
    ],

    # =========================
    # 3. JUDGMENT_RELATIONS (CRITICAL)
    # =========================
    # This prevents legal disasters by tracking overruling/following relationships
    "judgment_relations": [
        bigquery.SchemaField("from_doc_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("to_doc_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("relation_type", "STRING", mode="REQUIRED"),  # overrules, followed, distinguished
        bigquery.SchemaField("confidence", "FLOAT"),  # 0.0 to 1.0
        bigquery.SchemaField("source", "STRING"),  # llm, rule, manual
        bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],

    # =========================
    # 4. CHUNKS (With Embeddings)
    # =========================
    "chunks": [
        bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("chunk_type", "STRING"),  # ratio, obiter, clause, section, paragraph
        bigquery.SchemaField("text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("page_start", "INTEGER"),
        bigquery.SchemaField("page_end", "INTEGER"),
        bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),  # Vector embedding (768 dims)
        bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],

    # =========================
    # 5. DOMAIN_MAPPING
    # =========================
    "domain_mapping": [
        bigquery.SchemaField("document_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("primary_domain", "STRING", mode="REQUIRED"),  # education, labor, etc.
        bigquery.SchemaField("secondary_domains", "STRING", mode="REPEATED"),  # Array of secondary domains
        bigquery.SchemaField("confidence", "FLOAT"),  # Classification confidence
        bigquery.SchemaField("source", "STRING"),  # llm, keyword, manual
        bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],
}

# ============================================================================
# LEGACY GO SCHEMAS (Maintained for backward compatibility)
# ============================================================================
# These will be gradually migrated to unified schema
# ============================================================================

SCHEMAS = {

    # =========================
    # CORE IDENTITY (FACT ONLY)
    # =========================
    "go_master": [
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_number", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("department", "STRING"),
        bigquery.SchemaField("go_type", "STRING"),  # Mapping to go_archetype
        bigquery.SchemaField("raw_pdf_uri", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],

    # =========================
    # FUNCTIONAL THREAD MAPPING
    # =========================
    "go_functional_threads": [
        bigquery.SchemaField("thread_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("thread_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("role", "STRING"),  # primary / secondary
        bigquery.SchemaField("confidence", "FLOAT"),
        bigquery.SchemaField("source", "STRING"),  # llm / rule / manual
        bigquery.SchemaField("assigned_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],

    # =========================
    # CLAUSE SEMANTIC LAYER
    # =========================
    "go_clauses": [
        bigquery.SchemaField("clause_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("section_path", "STRING"),
        bigquery.SchemaField("clause_text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("clause_effect_type", "STRING"),  # introduce / amend / delete / clarify
        bigquery.SchemaField("functional_thread_ids", "STRING", mode="REPEATED"),
        bigquery.SchemaField("effective_from_date", "DATE"),
        bigquery.SchemaField("effective_to_date", "DATE"),
        bigquery.SchemaField("conditional_flags", "STRING"),  # JSON
        bigquery.SchemaField("visual_anchor_page", "INTEGER"),
        bigquery.SchemaField("visual_anchor_bbox", "STRING"),  # JSON
        bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
    ],

    # =========================
    # LEGAL RELATION GRAPH
    # =========================
    "go_legal_relations": [
        bigquery.SchemaField("relation_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target_go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("relation_type", "STRING", mode="REQUIRED"),  # amends / supersedes / clarifies
        bigquery.SchemaField("scope", "STRING"),  # full_go / clause
        bigquery.SchemaField("affected_thread_ids", "STRING", mode="REPEATED"),
        bigquery.SchemaField("confidence", "FLOAT"),
        bigquery.SchemaField("source", "STRING"),  # llm / rule
        bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],

    # =========================
    # ACT REFERENCES
    # =========================
    "go_act_links": [
        bigquery.SchemaField("link_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("act_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("act_year", "STRING"),  # Year extracted from act
        bigquery.SchemaField("section_reference", "STRING"),
        bigquery.SchemaField("relation_type", "STRING"),  # pursuant_to / overrides
        bigquery.SchemaField("confidence", "FLOAT"),  # Extraction confidence
    ],

    # =========================
    # DERIVED RESOLUTION OUTPUT
    # =========================
    "go_thread_resolution": [
        bigquery.SchemaField("resolution_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("functional_thread_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("active_go_ids", "STRING", mode="REPEATED"),
        bigquery.SchemaField("effective_clause_ids", "STRING", mode="REPEATED"),
        bigquery.SchemaField("thread_status", "STRING"),  # ACTIVE / SUPERSEDED
        bigquery.SchemaField("resolution_confidence", "FLOAT"),
        bigquery.SchemaField("resolution_version", "INTEGER"),
        bigquery.SchemaField("superseded_by_resolution_id", "STRING"),
        bigquery.SchemaField("last_updated", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],

    # =========================
    # SIDE TABLES (NORMALIZED)
    # =========================
    "go_beneficiaries": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("beneficiary_type", "STRING"),
        bigquery.SchemaField("beneficiary_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("count", "INTEGER"),
    ],

    "go_applicability": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("region_type", "STRING"),
        bigquery.SchemaField("region_name", "STRING", mode="REQUIRED"),
    ],

    "go_authorities": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("authority_role", "STRING"),  # issuer / approver
        bigquery.SchemaField("authority_name", "STRING", mode="REQUIRED"),
    ],

    "go_financials": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("amount", "FLOAT"),
        bigquery.SchemaField("currency", "STRING"),
        bigquery.SchemaField("budget_head", "STRING"),
        bigquery.SchemaField("commitment_type", "STRING"),  # recurring / one-time
        bigquery.SchemaField("source", "STRING"),  # llm / parsed
    ],

    # =========================
    # EFFECTS (STRICT ENUM)
    # =========================
    "go_effects": [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("effect_type", "STRING"),  # date / legal_effect
        bigquery.SchemaField("effect_role", "STRING"),  # issue_date / effective_from / retrospective_from
        bigquery.SchemaField("effect_value", "STRING"),
    ],

    # =========================
    # RELATION CANDIDATES (UNRESOLVED)
    # =========================
    "go_relation_candidates": [
        bigquery.SchemaField("candidate_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_go_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("target_ref_raw", "STRING", mode="REQUIRED"),  # Raw reference text
        bigquery.SchemaField("relation_type", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("confidence", "FLOAT"),
        bigquery.SchemaField("resolution_status", "STRING"),  # unresolved / low_confidence / error
        bigquery.SchemaField("resolution_error", "STRING"),
        bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],

    # =========================
    # INGESTION QUARANTINE
    # =========================
    "go_ingestion_errors": [
        bigquery.SchemaField("error_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("go_id", "STRING"),
        bigquery.SchemaField("phase", "STRING"),  # entity / relation / resolution
        bigquery.SchemaField("error_type", "STRING"),
        bigquery.SchemaField("raw_payload", "STRING"),
        bigquery.SchemaField("created_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP"),
    ],
}

# ============================================================================
# COMBINED SCHEMAS (For backward compatibility)
# ============================================================================
# Merge unified and legacy schemas for table creation
ALL_SCHEMAS = {**UNIFIED_SCHEMAS, **SCHEMAS}
