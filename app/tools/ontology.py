"""Skill ontology.

Two jobs:
  1. Give the JD agent a starting vocabulary so 'REST API development' and
     'FastAPI' are known to be the same requirement.
  2. Let the offline (mock) provider work without an LLM at all.

This is a seed, not a closed world. The LLM is still expected to add aliases it
sees in a specific JD - the ontology just stops it from having to rediscover
that Qdrant is a vector database every single run.
"""

from __future__ import annotations

from typing import Dict, List

SKILL_GRAPH: Dict[str, List[str]] = {
    "python": ["python", "python3", "py"],
    "agent_orchestration": [
        "langgraph", "crewai", "autogen", "semantic kernel", "agent orchestration",
        "multi-agent", "multi agent", "agentic", "agentic ai", "agent workflow",
    ],
    "langchain": ["langchain", "llama-index", "llamaindex"],
    "rag": [
        "rag", "retrieval augmented generation", "retrieval-augmented",
        "chunking", "reranking", "rerank", "hybrid search", "semantic search",
    ],
    "llm_applications": [
        "llm", "large language model", "gpt", "claude", "openai api", "prompt",
        "prompt engineering", "generative ai", "genai", "fine-tuning", "lora",
    ],
    "tool_calling": [
        "tool calling", "function calling", "tool use", "structured outputs",
        "json schema", "mcp", "model context protocol",
    ],
    "backend_api": [
        "fastapi", "flask", "django", "django rest", "rest api", "restful",
        "grpc", "microservice", "backend service", "api development",
    ],
    "cloud": [
        "aws", "azure", "gcp", "google cloud", "ec2", "ecs", "lambda", "s3",
        "eks", "fargate", "sagemaker", "azure openai",
    ],
    "vector_database": [
        "pinecone", "qdrant", "weaviate", "milvus", "chroma", "faiss",
        "pgvector", "vector database", "vector store", "embeddings",
    ],
    "containers_cicd": [
        "docker", "containeris", "containeriz", "ci/cd", "cicd", "github actions",
        "jenkins", "gitlab ci", "argocd", "continuous integration",
    ],
    "kubernetes": ["kubernetes", "k8s", "eks", "helm"],
    "mlops": [
        "mlflow", "kubeflow", "weights & biases", "wandb", "model registry",
        "experiment tracking", "feature store", "airflow",
    ],
    "observability": [
        "langsmith", "langfuse", "ragas", "observability", "tracing",
        "monitoring", "datadog", "evaluation harness",
    ],
    "classical_ml": [
        "scikit-learn", "sklearn", "xgboost", "lightgbm", "pytorch", "tensorflow",
        "random forest", "regression", "forecasting",
    ],
    "data_platform": [
        "databricks", "snowflake", "spark", "kafka", "dbt", "bigquery", "redshift",
    ],
    "databases": ["postgresql", "postgres", "mysql", "mongodb", "redis", "sql"],
    "production": [
        "production", "deployed", "shipped", "live", "in production", "scale",
        "uptime", "sla", "on-call", "incident",
    ],
}

# Phrases that suggest real delivery rather than familiarity.
IMPACT_MARKERS = [
    "designed", "built", "architected", "implemented", "deployed", "shipped",
    "owned", "led", "migrated", "reduced", "increased", "improved", "scaled",
    "launched", "raised", "cut", "drove", "introduced",
]

PRODUCTION_MARKERS = [
    "production", "requests/month", "requests per", "users", "students",
    "customers", "/day", "/week", "uptime", "live", "serving", "p99", "sla",
]

WEAK_MARKERS = ["familiar", "exposure", "basic", "worked on", "involved in", "aware of"]


def aliases_for(skill: str) -> List[str]:
    """All known surface forms for a skill string, including the skill itself."""
    s = skill.lower().strip()
    out = {s}
    for canonical, forms in SKILL_GRAPH.items():
        if s == canonical or s in forms or any(f in s for f in forms):
            out.update(forms)
            out.add(canonical.replace("_", " "))
    return sorted(out)


def canonical_for(text: str) -> List[str]:
    """Which ontology buckets a free-text string touches."""
    t = text.lower()
    return [c for c, forms in SKILL_GRAPH.items() if any(f in t for f in forms)]
