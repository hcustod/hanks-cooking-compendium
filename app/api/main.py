from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import recipes

app = FastAPI(title="HCC API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4321",
        "http://127.0.0.1:4321",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True}

# mount all /api routes
app.include_router(recipes.router)
