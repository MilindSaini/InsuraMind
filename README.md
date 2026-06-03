# InsuraMind

InsuraMind is an AI-powered insurance intelligence platform. Version 1 turns uploaded policy documents into cited answers, structured insight cards, risk flags, and document-level chat.

## Version 1 Scope

- Next.js frontend with auth screens, dashboard, upload, document viewer, insights, and chat.
- Spring Boot backend for auth, document upload, metadata, MinIO storage, chat orchestration, audit logs, and AI callbacks.
- FastAPI AI service for OCR/text extraction, document classification, semantic chunking, entity extraction, embeddings, retrieval, reranking, answer generation, and verification.
- PostgreSQL, Qdrant, MinIO, and Redis via Docker Compose.

## Local Prerequisites

- Java JDK 24 available at `C:\Program Files\Java\jdk-24`
- Maven 3.9+
- Python 3.12 with your existing packages installed
- Node.js 22+
- Docker Desktop

## Start Infrastructure

```powershell
Copy-Item .env.example .env
```

Fill in your Supabase PostgreSQL connection values and Gemini API key in `.env`, then start the shared services:

```powershell
docker-compose up -d qdrant minio redis
```

MinIO console: `http://localhost:9001`

Flyway creates the `insuramind` schema automatically on startup, so the backend and Supabase database stay aligned without manual SQL setup.

## Run Backend

```powershell
$env:JAVA_HOME='C:\Program Files\Java\jdk-24'
$env:Path="$env:JAVA_HOME\bin;$env:Path"
cd backend
mvn spring-boot:run
```

Backend API: `http://localhost:8080/api`

## Run AI Service

Use the existing conda environment named `InsuraMind` from Anaconda Navigator.

```powershell
conda activate InsuraMind
cd ai-services
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

AI health: `http://localhost:8001/health`

## Run Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

## First Test Flow

1. Sign up.
2. Upload a policy PDF.
3. Wait until the document status becomes `READY`.
4. Open the document page.
5. Ask: `What are the exclusions?`
6. Check citations, source snippets, insight cards, and risk flags.
