# CivicSathi
AI assistant that knows what government related tasks you need to complete, tells you exactly which documents you need, guides you through applications, reminds you about deadlines, and helps you avoid penalties. The biggest problem it solves is that people often don't know what they are supposed to do when their circumstances change.

## Setup

Use Python 3.11. Run the commands below from the repository root.

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe scripts/run_all.py
```

**macOS or Linux**

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python scripts/run_all.py
```

Run the copy command on first setup. Use fake demo data from `shared/samples.json`.

Open [backend health](http://localhost:8000/health) to check the backend. In a second terminal, use the same virtual environment's Python to run `python scripts/ping_all.py` and check all six MCP servers. Press Ctrl+C in the first terminal to stop the servers. Use `python scripts/run_all.py --only backend,documents` to start a subset.
