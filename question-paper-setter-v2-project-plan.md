# Question Paper Setter — V2 Project Plan

## 1. Project Goal

Build a production-style Question Paper Setter that accepts real-world PDF documents, extracts text/tables/figures, creates a searchable knowledge base, retrieves relevant source material, and uses an LLM to generate questions and complete question papers.

The V2 project is modular so Azure services, embedding models, LLMs, and vector databases can be replaced later without rewriting the application.

The learning goal is equally important: build the pipeline incrementally and understand each component instead of hiding everything behind a framework.

---

## 2. Target Architecture

```text
                         User / Teacher
                              |
                              v
                         Streamlit UI
                              |
                              v
                           FastAPI
                              |
                    Application Services
                              |
              +---------------+---------------+
              |                               |
              v                               v
       Document Pipeline                 Question Pipeline
              |                               |
              v                               v
   Azure Document Intelligence          Retrieval / RAG
              |                               |
              v                               v
       Document Normalizer               ChromaDB
              |                               |
              v                               v
       Context-Aware Chunking          Relevant Chunks
              |                               |
              v                               v
        Embedding Model                  LLM / Chat Model
              |                               |
              v                               v
          ChromaDB                    Question Generation
                                              |
                                              v
                                       Validation / Evaluation
                                              |
                                              v
                                        Question Paper
```

---

## 3. Technology Stack

### Core

- Python
- Git/GitHub
- pytest
- python-dotenv

### Document processing

- Azure AI Document Intelligence
- Initial model: `prebuilt-layout`
- Current development resource: Azure Document Intelligence F0

### GenAI framework

- LangChain

LangChain will be introduced after the core pipeline is understood. It should provide integrations and abstractions, not hide the entire application architecture.

### Embeddings

Potential providers:

- Azure OpenAI embeddings
- OpenAI embeddings
- Hugging Face / Sentence Transformers
- Other compatible embedding providers

Use an embedding abstraction so the provider can be changed later.

### Vector database

Initial POC:

- ChromaDB locally

Possible future alternatives:

- FAISS
- Qdrant
- Pinecone
- Azure AI Search
- Other vector stores

### LLM

Initial preferred cloud option:

- Azure OpenAI

Potential alternatives:

- OpenAI
- Ollama/local models
- Other LangChain-compatible models

### API/UI

- FastAPI
- Streamlit

---

## 4. Design Principles

### 4.1 Separate responsibilities

```text
Document Intelligence
    -> document extraction

Normalizer
    -> Azure result -> our internal representation

Chunker
    -> document -> retrieval-friendly chunks

Embedding provider
    -> text -> vector

Vector store
    -> vectors + metadata -> similarity search

Retriever
    -> query -> relevant chunks

LLM
    -> context + instructions -> generated questions

Validator
    -> generated questions -> quality checks
```

### 4.2 Avoid tight coupling to Azure

The rest of the application should not depend directly on Azure's `AnalyzeResult`.

```text
Azure AnalyzeResult
        |
        v
Normalizer
        |
        v
Our Document model
        |
        v
All downstream components
```

This makes it possible to replace Azure Document Intelligence later.

### 4.3 Conserve Azure credits

Do not repeatedly send the same PDF to Azure while experimenting.

Preferred flow:

```text
PDF
 |
 v
Azure Document Intelligence
 |
 v
Raw AnalyzeResult
 |
 v
JSON saved locally
```

Then parsing and normalization can be tested from saved data where practical.

---

# 5. Current Project Status

## Completed

### Phase 0 — Repository and environment

- GitHub repository created
- Python virtual environment created
- Initial project structure created
- Azure Document Intelligence F0 resource created
- `azure-ai-documentintelligence` installed

### Phase 1 — Azure Document Intelligence experiment

Successfully:

- Connected to Azure Document Intelligence
- Loaded endpoint/key using `.env`
- Created `AzureKeyCredential`
- Created `DocumentIntelligenceClient`
- Submitted a PDF
- Used `prebuilt-layout`
- Received `AnalyzeResult`
- Extracted text
- Observed OCR of text embedded inside images
- Inspected pages
- Inspected figures
- Inspected paragraphs
- Inspected tables
- Saved the raw Azure response as JSON

Current test document:

```text
gmail.pdf
```

It is a 2-page Gmail/email PDF containing text and figures. It is only a test document; the final system should remain generic and should not be Gmail-specific or textbook-specific.

---

# 6. What We Learned From Azure Document Intelligence

The actual result contains top-level fields including:

```text
apiVersion
modelId
stringIndexType
content
pages
tables
paragraphs
styles
contentFormat
sections
figures
```

The sample document contained:

```text
2 pages
0 tables
3 figures
```

Each page contained information such as:

```text
pageNumber
angle
width
height
unit
words
selectionMarks
lines
spans
```

Figures contained:

```text
id
boundingRegions
spans
elements
```

This is useful because figures can be associated with document elements and page locations.

Document Intelligence also extracted visible text embedded inside images. This demonstrates that the OCR/layout stage can capture text visually present in a PDF.

However, OCR extraction is different from semantic image understanding. A future vision-capable model may be used for important figures/diagrams when their meaning needs to be interpreted.

---

# 7. Current Internal Data Model

`app/models/document.py` currently contains:

```python
from dataclasses import dataclass


@dataclass
class DocumentElement:
    element_type: str
    content: str | None
    page_number: int
    metadata: dict


@dataclass
class Page:
    page_number: int
    width: float
    height: float
    elements: list[DocumentElement]


@dataclass
class Document:
    document_id: str
    source: str
    pages: list[Page]
    metadata: dict
```

These are intentionally simple.

They are not intended to reproduce the entire Azure `AnalyzeResult`. They represent the information our application needs.

---

# 8. Current Normalizer

`app/ingestion/document/normalizer.py` currently creates our `Document` and `Page` objects from Azure's result.

Current responsibility:

```text
Azure AnalyzeResult
        |
        v
Create Page objects
        |
        v
Create Document object
```

The current normalizer successfully produced:

```text
Document: gmail.pdf
Source: gmail.pdf
Number of pages: 2
Page: 1 Width: 8.5 Height: 11.0 Elements: 0
Page: 2 Width: 8.5 Height: 11.0 Elements: 0
```

The `elements` list is currently empty because paragraph/figure/table normalization has not yet been implemented.

---

# 9. Phase 2 — Complete Document Normalization

## Goal

Convert Azure's rich result into our generic document representation.

Target:

```text
Document
|
+-- Page 1
|   +-- Text
|   +-- Figure
|   +-- Text
|
+-- Page 2
    +-- Text
    +-- Figure
```

### Step 2.1 — Normalize paragraphs

Use Azure paragraphs as the primary source for logical text blocks.

Do not simply use `result.content` as all document content because it is consolidated reading-order text.

Do not duplicate content by independently adding words, lines, and paragraphs as separate text elements.

Determine the page of each paragraph using Azure page/bounding-region/span information.

Create:

```python
DocumentElement(
    element_type="text",
    content=paragraph.content,
    page_number=...,
    metadata={...}
)
```

and append it to the correct page.

### Step 2.2 — Normalize figures

Create figure elements from:

```text
result.figures
```

Preserve useful information such as:

- figure ID
- page
- bounding region
- related Azure elements
- spans

Initial representation can use `metadata`.

Example:

```python
DocumentElement(
    element_type="figure",
    content=None,
    page_number=1,
    metadata={
        "azure_figure_id": "...",
        "bounding_region": ...,
        "elements": [...]
    }
)
```

The actual figure image can be extracted later if needed for vision processing.

### Step 2.3 — Normalize tables

Create table elements from:

```text
result.tables
```

Preserve:

- row count
- column count
- cell contents
- page
- table location

Tables should remain structurally identifiable instead of being flattened blindly into ordinary text.

### Step 2.4 — Preserve semantic metadata

Azure may identify roles such as:

```text
pageHeader
pageFooter
pageNumber
sectionHeading
```

Preserve useful roles in metadata.

This allows later filtering. For example, page numbers and repetitive headers should normally not dominate embeddings.

---

# 10. Phase 3 — Document Chunking

## Goal

Convert normalized documents into retrieval-friendly chunks.

Do not start with blindly taking fixed character slices.

Consider:

- paragraph boundaries
- sections
- page boundaries
- headings
- tables
- figures
- semantic coherence
- chunk size
- overlap

Target:

```text
Document
    |
    v
Chunker
    |
    +--> Chunk 1
    +--> Chunk 2
    +--> Chunk 3
    ...
```

Each chunk should contain text plus metadata.

Example:

```python
{
    "id": "document_page_5_chunk_2",
    "text": "...",
    "metadata": {
        "source": "document.pdf",
        "page_start": 5,
        "page_end": 6,
        "content_types": ["text", "figure"]
    }
}
```

The exact chunking strategy will be evaluated rather than assumed to be optimal.

---

# 11. Phase 4 — Embedding Abstraction

## Goal

Convert chunks into vectors.

Do not hardcode one embedding provider throughout the application.

Conceptually:

```text
EmbeddingModel
     |
     +-- Azure OpenAI
     +-- OpenAI
     +-- Sentence Transformers
     +-- Other provider
```

The application should call something conceptually like:

```python
embedding_model.embed(text)
```

rather than directly depending everywhere on one provider.

Use the same embedding model/configuration consistently for document and query embeddings unless there is a deliberate reason to do otherwise.

---

# 12. Phase 5 — ChromaDB

For the POC, use ChromaDB locally.

```text
Chunks
 |
 v
Embedding model
 |
 v
Vectors
 |
 v
ChromaDB
```

Store metadata alongside each vector.

Useful metadata:

```text
document_id
source
page_start
page_end
chunk_id
content_types
section information when available
```

The vector store should not be responsible for document parsing or question generation.

---

# 13. Phase 6 — Retrieval

Build a retrieval layer:

```text
User query
    |
    v
Query embedding
    |
    v
Chroma similarity search
    |
    v
Top-K chunks
```

The retrieval component should return both content and metadata/source information so generated questions can be traced back to source pages.

---

# 14. Phase 7 — RAG

Combine retrieval with an LLM:

```text
Question generation request
            |
            v
       Retriever
            |
            v
    Relevant document chunks
            |
            v
      Prompt construction
            |
            v
           LLM
            |
            v
     Generated questions
```

The LLM should not be asked to generate questions from the entire document blindly. It should receive relevant context selected by retrieval.

---

# 15. Phase 8 — Question Generation

The question generator should eventually support parameters such as:

```text
Subject/topic
Difficulty
Number of questions
Question type
Marks
Learning objective
Source document
```

Potential question types:

```text
MCQ
Short answer
Long answer
True/False
Fill in the blank
Descriptive
Diagram-based
```

The exact set will be defined during implementation.

---

# 16. Phase 9 — Question Validation

Generated questions should be validated.

Potential checks:

### Relevance
Does the question relate to the retrieved source material?

### Grounding
Can the answer be supported by the source document?

### Duplication
Are multiple generated questions essentially the same?

### Difficulty
Does the question match the requested difficulty?

### Structure
Does an MCQ have valid options?

### Answer consistency
Does the supplied answer match the question?

---

# 17. Phase 10 — Multimodal Processing

After the basic text RAG system works, add multimodal support.

Current pipeline:

```text
PDF
 |
 v
Document Intelligence
 |
 +-- Text
 +-- Tables
 +-- Figure metadata
```

Future pipeline:

```text
Figure detected
      |
      v
Extract actual figure
      |
      v
Vision-capable model
      |
      v
Figure description / interpretation
      |
      v
Attach to document representation
```

For example:

```text
Text:
"Photosynthesis converts..."

Figure:
[diagram]

Vision description:
"Diagram showing the flow of sunlight..."
```

This combined representation can participate in retrieval and question generation.

Do not send every image to a vision model automatically. Only process figures when semantic understanding adds value, helping control cost.

---

# 18. Phase 11 — LangChain Integration

LangChain should be introduced after the underlying pipeline is understood.

Use it for useful integrations such as:

- LLM providers
- embedding providers
- vector stores
- retrievers
- prompt templates
- chains where useful

Do not make every internal object a LangChain object simply because LangChain supports it.

Preferred architecture:

```text
Our application
|
+-- ingestion
+-- normalization
+-- chunking
+-- embeddings
+-- retrieval
+-- generation
|
+-- LangChain adapters/integrations
```

---

# 19. Phase 12 — Model Switching

The architecture should support:

```text
LLM interface
     |
     +-- Azure OpenAI
     +-- OpenAI
     +-- Ollama
     +-- Other model
```

and:

```text
Embedding interface
     |
     +-- Azure OpenAI
     +-- Sentence Transformers
     +-- Other embedding provider
```

The rest of the application should not need to know which provider is active.

Configuration should determine the provider.

---

# 20. Phase 13 — FastAPI

FastAPI should be introduced after the core pipeline works.

Possible endpoints:

```text
POST /documents/upload
POST /documents/process
POST /documents/index
POST /questions/generate
POST /query
GET  /documents/{document_id}
GET  /questions/{question_set_id}
```

Architecture:

```text
Streamlit
    |
    v
FastAPI
    |
    v
Application Services
    |
    +-- Document pipeline
    +-- Retrieval
    +-- Generation
```

FastAPI should be the API layer, not the place where all business logic lives.

---

# 21. Phase 14 — Streamlit

Possible UI workflow:

```text
Upload PDF
     |
     v
Select processing options
     |
     v
Process / index document
     |
     v
Choose:
  - topic
  - difficulty
  - number of questions
  - question type
     |
     v
Generate
     |
     v
Review questions
     |
     v
Export question paper
```

---

# 22. Phase 15 — Evaluation

Evaluate the system instead of deciding that generated questions simply "look good."

Potential retrieval metrics:

- Precision@K
- Recall@K
- MRR where appropriate

Potential generation dimensions:

- Relevance
- Groundedness
- Correctness
- Diversity
- Difficulty alignment
- Duplicate rate

ROUGE/BLEU can be explored where appropriate, but they should not automatically be treated as the best metrics for every question-generation task.

---

# 23. Phase 16 — Testing

Use `pytest`.

Example:

```text
tests/
|
+-- test_normalizer.py
+-- test_chunker.py
+-- test_embeddings.py
+-- test_retriever.py
+-- test_question_generator.py
+-- test_validator.py
```

Avoid making every test call Azure.

Use saved fixtures/mocked responses where possible.

---

# 24. Phase 17 — Observability and Error Handling

Eventually add:

- structured logging
- meaningful exceptions
- retry handling
- API timeout handling
- model errors
- malformed documents
- empty retrieval results
- invalid generated questions

For cloud APIs, avoid silently failing.

---

# 25. Phase 18 — Cost Control

Because the project is being developed with limited Azure credits:

### Document Intelligence

- Use F0 during development where practical.
- Process representative small documents.
- Save results locally.
- Avoid repeated OCR of the same document.

### LLM

- Start with small/cheap models for development.
- Keep prompts short.
- Retrieve only necessary context.
- Avoid sending entire documents to the LLM.

### Embeddings

- Embed each chunk once.
- Persist the vector store.
- Do not regenerate embeddings unnecessarily.

### Vision

- Only send useful figures to a vision model.
- Cache figure descriptions.

---

# 26. Final Target Architecture

```text
                         +----------------+
                         |   Streamlit    |
                         +-------+--------+
                                 |
                                 v
                         +----------------+
                         |    FastAPI     |
                         +-------+--------+
                                 |
                     +-----------+-----------+
                     |                       |
                     v                       v
              Document Service       Question Service
                     |                       |
                     v                       v
        +-------------------------+   +-------------+
        | Azure Document          |   | Retriever   |
        | Intelligence            |   +------+------+
        +------------+------------+          |
                     |                       v
                     v                 +-------------+
              Raw AnalyzeResult       |  ChromaDB   |
                     |                 +------+------+
                     v                        |
               Normalizer                     v
                     |                 Relevant chunks
                     v                        |
               Document Model               |
                     |                       v
                     v                 +-------------+
              Contextual Chunker       | LLM         |
                     |                 +------+------+
                     v                        |
               Embedding Model               v
                     |                 Generated Questions
                     v                        |
                 ChromaDB                     v
                                       Validator
                                              |
                                              v
                                       Question Paper
```

---

# 27. Development Order

```text
1. Azure Document Intelligence
       DONE

2. Document dataclasses
       DONE

3. Page normalization
       DONE

4. Paragraph normalization
       NEXT

5. Figure normalization

6. Table normalization

7. Save/load normalized document

8. Chunking

9. Chunk metadata

10. Embedding abstraction

11. Embedding model

12. ChromaDB

13. Retrieval

14. RAG

15. LLM abstraction

16. Question generation

17. Question validation

18. Multimodal figure understanding

19. LangChain integrations

20. FastAPI

21. Streamlit

22. Evaluation

23. Testing

24. Cost optimization

25. Deployment
```

---

# 28. Immediate Next Task

We are currently here:

```text
Azure Document Intelligence
          |
          v
       Pages
          |
          v
       Document
          |
          v
   >>> NEXT: paragraphs <<<
```

The next coding task is to modify `normalizer.py` so that Azure paragraphs become `DocumentElement` objects.

We need to determine which page each paragraph belongs to using the information already returned by Azure.

Target:

```text
Document
|
+-- Page 1
|   +-- TextElement
|   +-- TextElement
|   +-- FigureElement
|   +-- TextElement
|
+-- Page 2
    +-- TextElement
    +-- FigureElement
```

Do not move to embeddings, ChromaDB, LangChain, or FastAPI yet.

The immediate objective is:

> Complete a generic, reusable document normalization layer first.

Once that works, the rest of the RAG pipeline can be built on top of a clean internal representation.
