#!/usr/bin/env python3
"""
Setup script for AI Airport Simulation - LLM Decision Making Playground

This package provides a sophisticated airport simulation designed specifically
for testing and comparing Large Language Models (LLMs) in air traffic control scenarios.
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements from requirements.txt
with open(os.path.join(this_directory, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="ai-airport-simulation",
    version="1.0.0",
    author="AI Airport Simulation Contributors",
    author_email="",
    description="LLM Decision Making Playground for Air Traffic Control Testing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-airport-simulation",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Games/Entertainment :: Simulation",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ai-airport-sim=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md", "*.txt"],
    },
    keywords=[
        "ai", "llm", "airport", "simulation", "air-traffic-control",
        "testing", "benchmarking", "aviation", "safety", "research"
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/ai-airport-simulation/issues",
        "Source": "https://github.com/yourusername/ai-airport-simulation",
        "Documentation": "https://github.com/yourusername/ai-airport-simulation/blob/main/README.md",
        "Changelog": "https://github.com/yourusername/ai-airport-simulation/blob/main/CHANGELOG.md",
    },
) 