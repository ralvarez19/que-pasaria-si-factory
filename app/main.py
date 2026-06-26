from fastapi import FastAPI

app = FastAPI(title="Qué pasaría si - Content Factory")

@app.get("/health")
def health():
    return {"status": "ok"}
