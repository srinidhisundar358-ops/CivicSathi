from fastapi import FastAPI

app = FastAPI(title="CivicSaathi")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
