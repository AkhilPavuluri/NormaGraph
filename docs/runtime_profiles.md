# Runtime profiles: local, cloud, and hybrid execution

NormaGraph is designed to support multiple execution environments through a **profile-based provider architecture**. The same pipeline stages apply across cloud, local, and mixed setups; differences are isolated in provider implementations rather than duplicated orchestration logic.

---

## Overview

Instead of scattering environment checks through business logic, the design centers on a **Provider layer** selected for the active runtime profile.

```
Query
  ↓
Orchestrator
  ↓
Provider layer
  ├── LLM Provider
  ├── Embedding Provider
  ├── Vector store
  └── Storage / document source
```

The **Orchestrator** contract stays stable; implementations behind each provider interface vary by profile.

---

## Status

The runtime profile system described in this document is part of the **planned architecture** and is **not fully implemented** in the current codebase.

It outlines the intended direction for supporting multiple execution environments (cloud, local, and hybrid) while maintaining a consistent pipeline and API surface.

**Current integration:** Backend and ingestion paths in this repository are wired for **Google Cloud** (Vertex / Gemini, BigQuery, GCS where configured) and **Qdrant**. The **frontend** exposes optional local model selection (e.g. Ollama) alongside cloud APIs.

---

## Runtime profiles

### Cloud

Production-oriented configuration using managed services.

- **LLM:** Gemini / Vertex AI  
- **Embeddings:** Vertex or API-backed embedding models  
- **Vector store:** Qdrant (managed or cloud endpoint)  
- **Storage:** Google Cloud Storage, BigQuery (as configured)

---

### Local

Offline or low-dependency execution using local infrastructure.

- **LLM:** Ollama (e.g. `qwen2.5:7b`, `mistral:7b`, `phi3:mini`)  
- **Embeddings:** Local models such as `bge-small-en`, `bge-base-en`, or `nomic-embed-text`  
- **Vector store:** Qdrant (local process) or Chroma  
- **Storage:** Local filesystem under `data/`, optional SQLite for metadata  

Cost and external dependency are minimized; retrieval quality depends on embedding and indexing choices as much as on the generation model.

---

### Hybrid

Mixed infrastructure: local components where appropriate, cloud where needed.

- **Embeddings:** local  
- **Vector store:** local  
- **LLM:** cloud (e.g. Gemini)

Balances latency, cost, and reasoning capability when full cloud retrieval is not required.

---

## Configuration

Runtime behavior is intended to be controlled through environment configuration:

```env
NORMAGRAPH_PROFILE=cloud   # cloud | local | hybrid
```

Exact variable names follow `.env.example` and service modules as they evolve. Under this model, the HTTP API surface stays fixed while provider implementations vary.

---

## Provider abstraction

Capabilities are expressed as interchangeable providers.

### LLM provider

```python
class LLMProvider:
    def generate(self, prompt: str) -> str:
        ...
```

Representative implementations: **Gemini** (cloud), **Ollama** (local).

---

### Embedding provider

- Cloud embedding APIs (Vertex / similar)  
- Local embedding models (BGE, Nomic, etc.)

---

### Vector store

- **Qdrant** (cloud or local URL)  
- **Chroma** (optional local deployment)

---

### Storage

- Cloud: GCS, BigQuery-backed tables  
- Local: filesystem paths, optional SQLite

---

## Provider resolution

A factory pattern can be used to select providers at runtime:

```python
def get_llm():
    if PROFILE == "local":
        return OllamaProvider()
    return GeminiProvider()
```

The same pattern applies to embeddings, vector clients, and storage adapters.

---

## System consistency

Across profiles:

- **Orchestrator** pipeline stages are unchanged  
- **REST API** routes and request shapes are unchanged  
- **Document and query schemas** stay aligned  

Only the backing providers change.

---

## Observability

Active runtime context can be surfaced for diagnostics (shape is illustrative):

```json
{
  "profile": "local",
  "llm": "ollama:qwen2.5",
  "vector_db": "qdrant(local)"
}
```

Transparency for debugging and operations without branching core logic in handlers.

---

## Retrieval quality (illustrative)

| Component   | Cloud   | Local    |
| ----------- | ------- | -------- |
| LLM         | High    | Moderate |
| Embeddings  | High    | High     |
| Vector DB   | High    | High     |

Structured retrieval quality is driven strongly by **embeddings and indexing**, not only by the chat model. Local stacks can remain viable for structured querying when those layers are tuned.

---

## Design constraints

The architecture avoids:

- Environment `if/else` across unrelated modules  
- Separate pipelines per environment  
- Incompatible schemas between modes  

One pipeline; provider substitution at the edges.

---

## Summary

NormaGraph is designed to support:

- **Cloud** — full managed stack  
- **Local** — minimal external dependency  
- **Hybrid** — selective cloud usage  

Flexibility at the infrastructure layer without forking application logic.

---

## Roadmap

- Introduce a unified provider abstraction layer aligned with runtime profiles  
- Add local and hybrid runtime profiles end-to-end in the backend  
- Align observability and status payloads with the active profile  
