"""
Setup configuration for DevDocAI v3.0.0

AI-Powered Documentation Generation System
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#') and not line.startswith('-')
        ]

setup(
    name="devdocai",
    version="3.0.0",
    author="DevDocAI Team",
    author_email="team@devdocai.com",
    description="AI-Powered Documentation Generation System for Solo Developers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0",
    packages=find_packages(exclude=["tests*", "docs*", "examples*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "pylint>=3.0.0",
            "mypy>=1.5.0",
        ],
        "llm": [
            "openai>=1.0.0",
            "anthropic>=0.7.0",
            "google-generativeai>=0.3.0",
        ],
        "performance": [
            "uvloop>=0.17.0",
            "redis>=4.5.0",
        ],
        "security": [
            "sqlcipher3>=0.5.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "devdocai=devdocai.cli.main_unified:main",
            "dda=devdocai.cli.main_unified:main",  # Short alias
        ],
    },
    include_package_data=True,
    package_data={
        "devdocai": [
            "templates/*.md",
            "templates/*.yml",
            "templates/*.json",
            "cli/templates/*",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/issues",
        "Source": "https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0",
        "Documentation": "https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/wiki",
    },
    keywords=[
        "documentation",
        "ai",
        "automation",
        "developer-tools",
        "cli",
        "code-documentation",
        "api-documentation",
        "markdown",
        "privacy-first",
        "offline-capable"
    ],
)