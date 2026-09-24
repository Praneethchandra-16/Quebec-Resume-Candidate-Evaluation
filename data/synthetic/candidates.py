"""
Synthetic candidate definitions.

These are the source of truth for the demo resumes. `scripts/generate_resumes.py`
renders each one into data/resumes/candidate_00X.pdf with *real* PDF link
annotations, so the URL extractor can be tested against both annotations and
raw text.

Design intent (see data/synthetic/ground_truth.json for the labels):
  001 extremely strong fit
  002 strong classical ML, weak GenAI
  003 strong GenAI depth, weak production/cloud
  004 strong backend/cloud, moderate AI
  005 strong RAG work but only ~2 years experience
  006 keyword-stuffed, no supporting accomplishments   <- must NOT rank top
  007 plain resume, excellent GitHub/portfolio evidence <- must climb after enrichment
  008 generally weak fit
"""

CANDIDATES = [
    # ------------------------------------------------------------------ 001
    {
        "id": "candidate_001",
        "name": "Aarav Menon",
        "title": "Senior AI Engineer",
        "location": "Hyderabad, India",
        "email": "aarav.menon@example.com",
        "phone": "+91 98xxx 41120",
        "links": {
            "linkedin": "https://www.linkedin.com/in/aarav-menon-ai",
            "github": "https://github.com/aaravmenon",
            "portfolio": "https://aaravmenon.dev",
        },
        "summary": (
            "AI engineer with 6.5 years building and operating production Python "
            "services, the last 3 focused on LLM applications and multi-agent "
            "workflows serving internal business users."
        ),
        "skills": {
            "Languages": "Python, SQL, TypeScript, Bash",
            "AI / LLM": "LangChain, LangGraph, RAG, function calling, prompt evaluation, LangSmith",
            "Data / Retrieval": "Qdrant, pgvector, FAISS, text-embedding-3-large",
            "Backend": "FastAPI, Celery, PostgreSQL, Redis",
            "Cloud / Ops": "AWS (ECS, Lambda, S3), Docker, GitHub Actions, Terraform basics",
        },
        "experience": [
            {
                "title": "Senior AI Engineer",
                "company": "Zenlytix Technologies",
                "dates": "Mar 2023 - Present",
                "bullets": [
                    "Designed a LangGraph multi-agent workflow for customer-support triage: "
                    "a router node, three specialist nodes and a human-review checkpoint, "
                    "handling ~180k requests/month in production.",
                    "Implemented tool calling across 6 internal REST APIs with typed Pydantic "
                    "schemas and strict structured outputs; reduced malformed-call rate from 9% to 0.4%.",
                    "Built the RAG layer over 240k support documents using Qdrant and "
                    "text-embedding-3-large; raised retrieval recall@5 from 0.61 to 0.88 by "
                    "moving to section-aware chunking and adding a rerank stage.",
                    "Deployed everything behind FastAPI on AWS ECS Fargate with GitHub Actions "
                    "CI/CD; added LangSmith tracing and per-run cost attribution.",
                    "Owned an offline evaluation suite (180 labelled queries) run on every PR.",
                ],
            },
            {
                "title": "Backend Engineer",
                "company": "Finlytics Systems",
                "dates": "Jul 2019 - Feb 2023",
                "bullets": [
                    "Built Python/FastAPI microservices for a payments reconciliation platform "
                    "processing 4M records/day.",
                    "Containerised 14 services with Docker and moved deployments to ECS; cut "
                    "release time from 45 minutes to under 8.",
                    "Introduced pytest-based contract tests and raised coverage from 22% to 76%.",
                ],
            },
        ],
        "projects": [
            {
                "name": "enterprise-agentic-rag (open source)",
                "text": "Reference LangGraph + FastAPI + Qdrant agent with Docker Compose "
                        "deployment and an evaluation harness. 340 GitHub stars.",
            }
        ],
        "education": ["B.Tech, Computer Science - NIT Warangal, 2019"],
        "certifications": ["AWS Certified Solutions Architect - Associate (2022)"],
    },

    # ------------------------------------------------------------------ 002
    {
        "id": "candidate_002",
        "name": "Priya Ramanathan",
        "title": "Machine Learning Engineer",
        "location": "Bengaluru, India",
        "email": "priya.ramanathan@example.com",
        "phone": "+91 99xxx 20087",
        "links": {
            "linkedin": "https://www.linkedin.com/in/priya-ramanathan-ml",
            "github": "https://github.com/priya-ram",
        },
        "summary": (
            "ML engineer with 8 years shipping supervised learning systems in "
            "retail and logistics. Deep experience in feature pipelines, model "
            "training at scale and MLOps."
        ),
        "skills": {
            "Languages": "Python, SQL, Scala",
            "ML": "scikit-learn, XGBoost, PyTorch, TensorFlow, time-series forecasting",
            "MLOps": "MLflow, Airflow, Kubeflow, SageMaker, Kubernetes",
            "Cloud": "AWS (SageMaker, EMR, S3), Docker, Jenkins",
            "Data": "Spark, Databricks, Snowflake, Feast",
        },
        "experience": [
            {
                "title": "Lead ML Engineer",
                "company": "Cartwheel Retail Group",
                "dates": "Jan 2021 - Present",
                "bullets": [
                    "Own demand-forecasting models for 12,000 SKUs; reduced forecast MAPE "
                    "from 18.4% to 11.9% using gradient-boosted trees with hierarchical reconciliation.",
                    "Built the training platform on SageMaker with MLflow tracking and "
                    "Kubernetes-based batch inference serving 40M predictions/week.",
                    "Ran a pilot using the OpenAI API to summarise merchandiser notes into "
                    "structured fields; shipped as a small internal tool.",
                    "Mentored 5 engineers; introduced model cards and drift monitoring.",
                ],
            },
            {
                "title": "Data Scientist",
                "company": "Trellis Logistics",
                "dates": "Aug 2017 - Dec 2020",
                "bullets": [
                    "Built route-ETA models in PyTorch; deployed via Flask services on EC2.",
                    "Designed Spark feature pipelines over 2TB/day of telemetry.",
                ],
            },
        ],
        "projects": [],
        "education": [
            "M.Tech, Data Science - IIT Madras, 2017",
            "B.E., Electronics - Anna University, 2015",
        ],
        "certifications": ["Databricks Certified ML Professional (2023)"],
    },

    # ------------------------------------------------------------------ 003
    {
        "id": "candidate_003",
        "name": "Rohit Verma",
        "title": "Applied Research Engineer, GenAI",
        "location": "Pune, India",
        "email": "rohit.verma@example.com",
        "phone": "+91 90xxx 77341",
        "links": {
            "linkedin": "https://www.linkedin.com/in/rohitverma-genai",
            "github": "https://github.com/rohit-verma-ml",
            "portfolio": "https://rohitverma.ai",
        },
        "summary": (
            "4 years of applied GenAI work: fine-tuning, retrieval research and "
            "agent prototypes. Strong on model behaviour and evaluation, lighter "
            "on cloud operations."
        ),
        "skills": {
            "Languages": "Python",
            "AI / LLM": "Transformers, LoRA, QLoRA, DPO, RAG, LangChain, LangGraph, Ragas",
            "Retrieval": "FAISS, ColBERT, hybrid BM25 + dense retrieval",
            "Tooling": "PyTorch, HuggingFace, Weights & Biases, vLLM",
            "Other": "Docker (basic), Git",
        },
        "experience": [
            {
                "title": "Applied Research Engineer",
                "company": "Aeon AI Labs",
                "dates": "Jun 2022 - Present",
                "bullets": [
                    "Fine-tuned Llama-3 8B with QLoRA for a legal-summarisation task; "
                    "beat the zero-shot baseline by 14 ROUGE-L points on an internal set.",
                    "Prototyped a LangGraph research agent that plans, searches and writes "
                    "literature reviews; ran as an internal demo, not productionised.",
                    "Built a retrieval evaluation harness with Ragas covering faithfulness "
                    "and context precision across 5 chunking strategies.",
                    "Published 2 workshop papers on retrieval-augmented summarisation.",
                ],
            },
            {
                "title": "ML Intern -> Associate Engineer",
                "company": "Vertex Research",
                "dates": "Jul 2021 - May 2022",
                "bullets": [
                    "Trained sentence-embedding models for semantic search over patents.",
                ],
            },
        ],
        "projects": [
            {
                "name": "agentic-lit-review",
                "text": "LangGraph agent that decomposes a research question, searches arXiv "
                        "and drafts a review. Runs locally; no deployment.",
            }
        ],
        "education": ["M.S., Computer Science - IIIT Hyderabad, 2021"],
        "certifications": [],
    },

    # ------------------------------------------------------------------ 004
    {
        "id": "candidate_004",
        "name": "Daniel Okafor",
        "title": "Senior Backend / Platform Engineer",
        "location": "Remote (Lagos, Nigeria)",
        "email": "daniel.okafor@example.com",
        "phone": "+234 80x xxx 4412",
        "links": {
            "linkedin": "https://www.linkedin.com/in/danielokafor-platform",
            "github": "https://github.com/dokafor",
        },
        "summary": (
            "7 years of backend and platform engineering. Strong Python, AWS and "
            "Kubernetes. Started integrating LLM features into product surfaces in 2024."
        ),
        "skills": {
            "Languages": "Python, Go, SQL",
            "Backend": "FastAPI, Django REST, gRPC, PostgreSQL, Kafka",
            "Cloud / Ops": "AWS (EKS, ECS, Lambda, RDS), Kubernetes, Terraform, Docker, ArgoCD",
            "AI / LLM": "OpenAI API, RAG (pgvector), prompt templating",
            "CI/CD": "GitHub Actions, Jenkins, Datadog",
        },
        "experience": [
            {
                "title": "Senior Platform Engineer",
                "company": "Kite Commerce",
                "dates": "Feb 2021 - Present",
                "bullets": [
                    "Own a 60-service Kubernetes platform on EKS; drove p99 latency down 38% "
                    "through connection pooling and autoscaling policy work.",
                    "Built an internal RAG-backed documentation assistant using pgvector and "
                    "the OpenAI API, served from FastAPI; ~900 weekly internal users.",
                    "Standardised CI/CD across 60 repos with GitHub Actions and ArgoCD.",
                    "Implemented function calling for a support-ticket classifier that routes "
                    "to internal APIs.",
                ],
            },
            {
                "title": "Backend Engineer",
                "company": "Paystream",
                "dates": "Sep 2018 - Jan 2021",
                "bullets": [
                    "Built Django REST and FastAPI services for a payments gateway.",
                    "Migrated batch jobs to Kafka streaming; cut settlement lag from 30m to 90s.",
                ],
            },
        ],
        "projects": [],
        "education": ["B.Sc., Computer Science - University of Lagos, 2018"],
        "certifications": [
            "Certified Kubernetes Administrator (2022)",
            "AWS Certified DevOps Engineer - Professional (2023)",
        ],
    },

    # ------------------------------------------------------------------ 005
    {
        "id": "candidate_005",
        "name": "Sneha Iyer",
        "title": "AI Engineer",
        "location": "Chennai, India",
        "email": "sneha.iyer@example.com",
        "phone": "+91 87xxx 55190",
        "links": {
            "linkedin": "https://www.linkedin.com/in/sneha-iyer-ai",
            "github": "https://github.com/snehaiyer-dev",
            "portfolio": "https://sneha-iyer.vercel.app",
        },
        "summary": (
            "2 years of focused RAG and LLM application work. Fast learner with "
            "genuine production exposure at small scale."
        ),
        "skills": {
            "Languages": "Python, JavaScript",
            "AI / LLM": "LangChain, LangGraph, RAG, function calling, OpenAI API, Claude API",
            "Retrieval": "Chroma, Qdrant, hybrid search, reranking",
            "Backend": "FastAPI, Streamlit, SQLite, PostgreSQL",
            "Ops": "Docker, GitHub Actions, Render, Fly.io",
        },
        "experience": [
            {
                "title": "AI Engineer",
                "company": "Brightpath EdTech",
                "dates": "Sep 2024 - Present",
                "bullets": [
                    "Built the course-content assistant: RAG over 18k lesson pages with "
                    "Qdrant, hybrid retrieval and a rerank stage; serves 12k students.",
                    "Added a LangGraph flow with a grading node and retry edge to catch "
                    "unsupported answers before they reach students.",
                    "Wrote a 120-question evaluation set and tracked faithfulness weekly.",
                    "Shipped with FastAPI + Docker to Fly.io; set up GitHub Actions CI.",
                ],
            },
            {
                "title": "Junior Developer",
                "company": "Brightpath EdTech",
                "dates": "Aug 2023 - Aug 2024",
                "bullets": [
                    "Built internal dashboards in Streamlit and REST endpoints in FastAPI.",
                ],
            },
        ],
        "projects": [
            {
                "name": "rag-eval-playground",
                "text": "Open-source comparison of 6 chunking strategies with a reproducible "
                        "evaluation notebook.",
            }
        ],
        "education": ["B.E., Information Technology - Anna University, 2023"],
        "certifications": [],
    },

    # ------------------------------------------------------------------ 006
    {
        "id": "candidate_006",
        "name": "Vikram Shetty",
        "title": "Senior AI/ML Engineer | Agentic AI | LLMOps | RAG Expert",
        "location": "Mumbai, India",
        "email": "vikram.shetty@example.com",
        "phone": "+91 93xxx 66104",
        "links": {
            "linkedin": "https://www.linkedin.com/in/vikram-shetty-ai-expert",
            "github": "https://github.com/vikramshetty99",
        },
        "summary": (
            "Results-driven Senior AI Engineer with expertise in Agentic AI, LangGraph, "
            "LangChain, RAG, MCP, Vector Databases, LLMOps, Kubernetes, AWS, Azure, GCP, "
            "MLflow, Databricks, Snowflake, FastAPI, Docker, CI/CD and Production AI Systems."
        ),
        "skills": {
            "AI / LLM": "LangGraph, LangChain, CrewAI, AutoGen, Semantic Kernel, RAG, GraphRAG, "
                        "Agentic AI, Multi-Agent Systems, MCP, Function Calling, Prompt Engineering, "
                        "Fine-tuning, RLHF, LLMOps",
            "Vector DBs": "Pinecone, Qdrant, Weaviate, Milvus, Chroma, FAISS, pgvector",
            "Cloud": "AWS, Azure, GCP, Kubernetes, Docker, Terraform, Jenkins, ArgoCD",
            "Data": "Databricks, Snowflake, Spark, Kafka, Airflow, dbt, MLflow, Kubeflow",
            "Backend": "FastAPI, Flask, Django, Node.js, GraphQL, Microservices",
        },
        "experience": [
            {
                "title": "Senior AI/ML Engineer",
                "company": "Global Tech Solutions Pvt Ltd",
                "dates": "Apr 2022 - Present",
                "bullets": [
                    "Worked on Agentic AI, LangGraph, LangChain and RAG based solutions.",
                    "Involved in end-to-end development of AI/ML and GenAI applications.",
                    "Responsible for Vector Database, LLMOps and Production AI deployment activities.",
                    "Coordinated with stakeholders and participated in Agile ceremonies.",
                    "Used AWS, Azure, Kubernetes, Docker and CI/CD in the project.",
                ],
            },
            {
                "title": "Software Engineer",
                "company": "Infotech Consultancy Services",
                "dates": "Jun 2018 - Mar 2022",
                "bullets": [
                    "Worked on Python, Java and SQL based enterprise applications.",
                    "Involved in requirement gathering, development, testing and support.",
                ],
            },
        ],
        "projects": [
            {
                "name": "AI Chatbot Project",
                "text": "Developed AI chatbot using LangChain, LangGraph, RAG and Vector DB.",
            }
        ],
        "education": ["B.E., Computer Engineering - Mumbai University, 2018"],
        "certifications": [
            "Generative AI Certification (online)",
            "Agentic AI Masterclass Certificate",
        ],
    },

    # ------------------------------------------------------------------ 007
    {
        "id": "candidate_007",
        "name": "Meera Krishnan",
        "title": "Software Engineer",
        "location": "Kochi, India",
        "email": "meera.krishnan@example.com",
        "phone": "+91 85xxx 33027",
        "links": {
            "github": "https://github.com/meerak-builds",
            "portfolio": "https://meerakrishnan.com",
        },
        "summary": (
            "Software engineer, 5 years. Backend services and internal tooling. "
            "Most of my AI work is on my own time - see GitHub and portfolio."
        ),
        "skills": {
            "Languages": "Python, Java, SQL",
            "Backend": "FastAPI, Spring Boot, PostgreSQL",
            "Other": "Docker, Git, Jenkins, AWS (EC2, S3)",
        },
        "experience": [
            {
                "title": "Software Engineer",
                "company": "Marlin Systems",
                "dates": "Jul 2021 - Present",
                "bullets": [
                    "Maintain and extend Python/FastAPI services for an inventory platform.",
                    "Wrote data-migration tooling and internal admin APIs.",
                    "Dockerised legacy services and set up Jenkins pipelines.",
                ],
            },
            {
                "title": "Associate Engineer",
                "company": "Marlin Systems",
                "dates": "Aug 2019 - Jun 2021",
                "bullets": [
                    "Java backend maintenance and bug fixing.",
                    "Wrote SQL reports for the operations team.",
                ],
            },
        ],
        "projects": [
            {
                "name": "Side projects",
                "text": "Several LLM agent and retrieval projects built outside work. "
                        "Details, code and write-ups are on my GitHub and portfolio.",
            }
        ],
        "education": ["B.Tech, Computer Science - CUSAT, 2019"],
        "certifications": [],
    },

    # ------------------------------------------------------------------ 008
    {
        "id": "candidate_008",
        "name": "Arjun Desai",
        "title": "Senior Data Analyst",
        "location": "Ahmedabad, India",
        "email": "arjun.desai@example.com",
        "phone": "+91 97xxx 11458",
        "links": {
            "linkedin": "https://www.linkedin.com/in/arjun-desai-analytics",
        },
        "summary": (
            "6 years in business analytics and reporting for manufacturing and FMCG clients."
        ),
        "skills": {
            "Analytics": "SQL, Excel (advanced), Power BI, Tableau, Google Analytics",
            "Programming": "Python (pandas, matplotlib), VBA",
            "Statistics": "A/B testing, regression, forecasting (Prophet)",
            "Other": "Snowflake, dbt (basic), Jira",
        },
        "experience": [
            {
                "title": "Senior Data Analyst",
                "company": "Meridian Consumer Goods",
                "dates": "Mar 2020 - Present",
                "bullets": [
                    "Own the commercial reporting layer: 40+ Power BI dashboards across sales, "
                    "supply and finance.",
                    "Built SQL models in Snowflake feeding weekly executive reporting.",
                    "Ran pricing A/B tests across 300 stores; presented findings to leadership.",
                    "Used ChatGPT to speed up SQL drafting and documentation.",
                ],
            },
            {
                "title": "Data Analyst",
                "company": "Sunfield Manufacturing",
                "dates": "Jun 2018 - Feb 2020",
                "bullets": [
                    "Automated Excel reporting with VBA and Python scripts.",
                    "Built demand dashboards for plant managers.",
                ],
            },
        ],
        "projects": [],
        "education": ["MBA, Business Analytics - NMIMS, 2018", "B.Com - Gujarat University, 2015"],
        "certifications": ["Microsoft Certified: Power BI Data Analyst Associate (2021)"],
    },
]
