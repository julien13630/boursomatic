"""
Boursomatic Backend API
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="Boursomatic API",
    description="MVP platform for stock market recommendations",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Boursomatic API",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "dev"),
    }


@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "dev"),
    }


@app.get("/metrics")
async def metrics():
    """Metrics endpoint (placeholder for Prometheus)"""
    return {
        "http_requests_total": 0,
        "http_500_total": 0,
    }
