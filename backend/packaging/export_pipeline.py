import os
import shutil
import sys
from pathlib import Path

def export_insight_engine(output_dir: str = "dist/insight_engine"):
    """
    Export the core insight engine as a standalone package.
    """
    # Path(__file__) is backend/packaging/export_pipeline.py
    # .parent is backend/packaging
    # .parent.parent is backend
    backend_dir = Path(__file__).parent.parent
    app_dir = backend_dir / "app"
    
    # Output to dist/insight_engine relative to project root (parent of backend)
    project_root = backend_dir.parent
    output_path = project_root / output_dir
    
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True)
    
    print(f"📦 Exporting Insight Engine to {output_path}...")
    
    # 1. Copy core modules
    core_modules = [
        "llm.py",
        "ranking_engine.py",
        "market_signals.py",
        "config.py",
        "schemas.py",
        "supabase_client.py",
        "__init__.py"
    ]
    
    package_dir = output_path / "social_stocks_engine"
    package_dir.mkdir()
    
    for module in core_modules:
        src = app_dir / module
        if src.exists():
            shutil.copy2(src, package_dir / module)
            print(f"  - Copied {module}")
        else:
            # Create empty __init__.py if missing
            if module == "__init__.py":
                (package_dir / module).touch()
            else:
                print(f"  ⚠️ Warning: {module} not found!")

    # 2. Create setup.py
    setup_content = """
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
"""
    with open(output_path / "setup.py", "w") as f:
        f.write(setup_content)
    print("  - Created setup.py")
    
    # 3. Create Dockerfile for microservice usage
    dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

# Example entrypoint (if wrapping in a service)
# CMD ["python", "-m", "social_stocks_engine.main"]
"""
    with open(output_path / "Dockerfile", "w") as f:
        f.write(dockerfile_content)
    print("  - Created Dockerfile")
    
    # 4. Create README
    readme_content = """
# Social Stocks Insight Engine

This package encapsulates the LLM-driven insight processing pipeline.

## Usage

```python
from social_stocks_engine.ranking_engine import get_ranker
from social_stocks_engine.llm import call_openrouter_chat

# Rank posts
ranker = get_ranker("balanced")
ranked_posts = ranker.rank_posts(posts)
```
"""
    with open(output_path / "README.md", "w") as f:
        f.write(readme_content)
    print("  - Created README.md")
    
    print(f"✅ Export complete! Package located at: {output_path}")

if __name__ == "__main__":
    export_insight_engine()
