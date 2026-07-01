# AICop

AICop is a multi-agent AI investigation platform that evaluates the security, reliability, and trustworthiness of AI systems.

## What is included
- FastAPI backend with investigation endpoints
- LangGraph-style orchestrator with planner, security, reliability, evaluator, and report agents
- SQLite persistence for investigation cases
- Streamlit frontend for running investigations and viewing reports
- PDF report generation support

## Run the backend
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Run the frontend
```bash
streamlit run frontend/app.py
```

## Verify the API
```bash
curl http://127.0.0.1:8000/health
```
