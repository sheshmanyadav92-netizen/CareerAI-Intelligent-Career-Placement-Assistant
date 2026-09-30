from fastapi import FastAPI

app = FastAPI(title="CareerAI API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
