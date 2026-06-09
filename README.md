# TechSupportKG

A technical support system that answers natural language questions about software libraries using a Knowledge Graph (KG) and a Large Language Model (LLM). Built as a research prototype to explore the intersection of Knowledge Representation, NL-to-SPARQL translation, and agentic reasoning loops.

---

## Motivation

Enterprise support systems like SAP's handle thousands of queries about software versions, breaking changes, and compatibility issues. This project explores whether a small, explainable KG-based system can answer such queries accurately — combining the structured reasoning of SPARQL with the natural language understanding of LLMs.

---

## Architecture

```
User question (natural language)
        │
        ▼
┌─────────────────────┐
│   generate_sparql() │  ← Few-shot prompting with ontology schema
│   LLM (llama-3.1)   │
└────────┬────────────┘
         │  SPARQL query
         ▼
┌─────────────────────┐
│   rdflib graph      │  ← ontology.ttl (RDF/OWL)
│   SPARQL engine     │
└────────┬────────────┘
         │
    ┌────┴──────────────────────┐
    │                           │
 Syntax error              0 results
    │                           │
    ▼                           ▼
reformulate()              verify()
(fix the query)        (relax constraints)
    │                           │
    └──────────┬────────────────┘
               │  results
               ▼
┌─────────────────────┐
│  generate_answer()  │  ← LLM synthesizes natural language response
└─────────────────────┘
```

---

## Knowledge Graph

### Ontology

Defined in RDF/OWL using `rdflib`. Five classes, five object properties, five datatype properties.

**Classes:** `Library`, `Version`, `Module`, `Change`, `Language`

**Object properties:**
- `Library → hasVersion → Version`
- `Library → hasModule → Module`
- `Version → hasChange → Change`
- `Change → changeModule → Module`
- `Library → requires → Language`

**Datatype properties:**
- `Library.libraryName` (xsd:string)
- `Version.versionNumber` (xsd:string)
- `Change.typeChange` (xsd:string) — values: `breaking`, `feature`, `bugfix`
- `Change.descriptionChange` (xsd:string)
- `Change.fixChange` (xsd:string)

### Data Ingestion

Data is automatically ingested from the GitHub Releases API. The pipeline:

1. Fetches the 5 most recent stable releases of TensorFlow (excluding release candidates)
2. Parses release notes markdown — extracting breaking changes, features, and bugfixes per module
3. Generates unique URIs using `version + md5(description)[:8]` to avoid collisions
4. Populates the RDF graph and serializes to `ontology.ttl`

**Graph size:** ~80 triples covering TensorFlow versions 2.18.1 → 2.21.0

---

## NL-to-SPARQL Agent

### Approach

Few-shot prompting: the system prompt includes the ontology schema and 4 curated examples of (question → SPARQL) pairs. No fine-tuning required.

**Key design decisions:**
- Literals must use `^^xsd:string` typing for rdflib to match them correctly
- Module URIs follow the convention `Module_tf_lite` (dots replaced by underscores)
- `OPTIONAL {}` is used for nullable properties like `fixChange`

### Reformulation Loop

The agent handles two failure modes:

| Failure | Detection | Recovery |
|---|---|---|
| Syntax error | `rdflib` raises exception | `reformulate()`: send error back to LLM to fix |
| Empty results | `len(results) == 0` | `verify()`: ask LLM to relax query constraints |

Both recovery functions retry up to 10 times before returning a fallback message.

---

## Stack

| Component | Technology |
|---|---|
| Knowledge Graph | `rdflib` (Python), RDF/OWL, Turtle format |
| SPARQL engine | `rdflib` built-in SPARQL processor |
| LLM | `llama-3.1-8b-instant` via Groq API |
| Data source | GitHub Releases API |
| Evaluation | LLM-as-a-judge (`llama-3.1-8b-instant`) |

---

## How to Run

### Prerequisites

```bash
pip install rdflib groq requests
export GROQ_API_KEY=your_key_here
```

### 1. Build the knowledge graph

```bash
python populate_graph.py
```

Fetches TensorFlow releases from GitHub and generates `ontology.ttl`.

### 2. Run the agent and benchmark

```bash
python sparql_generator.py
```
> Reads `benchmark.json` (15 ground-truth question-answer pairs), evaluates each one, and prints per-question results plus a summary.

---

## Benchmark Results

**15 questions** covering: breaking changes, features, bugfixes, module-specific queries, version-specific queries, and questions with no answer in the graph.

| Metric | Score |
|---|---|
| Syntactically valid SPARQL queries | 15 / 15 |
| Semantically correct answers | 12 / 15 |

> **Note:** Results may vary across runs due to the non-deterministic nature of LLM outputs, even with low temperature settings.

### Failure analysis

The 3 remaining failures share a common root cause: `verify()` fails to relax queries that combine module filters with version filters — the relaxed query remains too restrictive and returns 0 results.

Affected questions:
- *Was there any change related to JPEG in TensorFlow?*
- *In which version was tf.lite deprecated?*
- *Does TensorFlow support Python 3.9 in version 2.21.0?*

---

## Limitations & Future Work

**1. Few-shot prompting does not generalize well**
The LLM was observed to over-apply filters (e.g., searching for "TensorFlow" inside module URIs) for questions outside the few-shot distribution. This is a known limitation of prompt-based NL-to-SPARQL — solutions include fine-tuning on domain-specific (question, SPARQL) pairs or grammar-constrained decoding.

**2. `verify()` relaxation is unreliable**
When a query returns 0 results, the agent asks the LLM to generate a more general version. This works for simple queries but fails for compound filters. A more robust approach would be systematic constraint removal (e.g., strip filters one by one) rather than relying on the LLM to infer which constraint to relax.

**3. LLM-as-a-judge is sensitive to prompt wording**
The same evaluation run with two different judge prompts produced scores of 5/15 and 12/15. The judge conflated answer completeness with correctness, and was sensitive to minor phrasing differences. Findings: judge prompts require explicit instruction to evaluate semantic equivalence, not surface-level matching.

**4. Literal datatype matching**
rdflib's SPARQL engine requires typed literals (`"breaking"^^xsd:string`) in triple patterns. Plain literals (`"breaking"`) do not match typed ones. This must be explicitly taught through few-shot examples — it is not handled automatically by the LLM.

**5. LLM output consistency**
Both the SPARQL generator and the LLM-as-a-judge produce variable outputs across runs, even at low temperatures. Future work should explore techniques to improve consistency: structured output constraints, self-consistency sampling (majority vote over multiple generations), or deterministic grammar-guided decoding.

**6. Static knowledge graph**
The graph is rebuilt from scratch on each run. A production system would use a persistent triple store (Apache Jena, GraphDB, Oxigraph) with a SPARQL endpoint, and support incremental updates as new releases are published.

---

## Project Structure

```
techsupport-kg/
├── ontology.ttl          # Serialized RDF graph (Turtle format)
├── populate_graph.py     # Ontology definition + GitHub ingestion pipeline
├── parse_release.py      # Markdown parser for GitHub release notes
├── sparql_generator.py   # NL-to-SPARQL agent + benchmark runner (generate, reformulate, verify, answer, evaluate)
├── query_tester.py       # Manual SPARQL query tester against ontology.ttl
└── benchmark.json        # 15 ground-truth question-answer pairs
```
