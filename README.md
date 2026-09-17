# AI Support Ticket Decision Assistant

A small FastAPI and Streamlit application that authenticates users, stores support tickets in SQLite, retrieves relevant local policy documents, and asks OpenAI `gpt-4.1-mini` for a validated next action.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in `.env` for live AI decisions. Without a key, the service safely returns `NEEDS_MORE_INFORMATION` when policy context exists.

## Run

From the project root, use two terminals:

```powershell
uvicorn backend.main:app --reload
streamlit run frontend/app.py
```

Open the Streamlit URL shown in the terminal. The API is available at `http://localhost:8000/docs`.

## Test

```powershell
pytest -q
```
