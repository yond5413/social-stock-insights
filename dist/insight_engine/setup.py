
from setuptools import setup, find_packages

setup(
    name="social-stocks-engine",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "pydantic",
        "httpx",
        "yfinance",
        "supabase",
        "python-dotenv",
        "cohere"
    ],
    author="Social Stocks Insights",
    description="LLM-driven financial insight processing pipeline",
)
