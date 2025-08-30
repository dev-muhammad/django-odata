#!/usr/bin/env python
"""
Setup script for django-odata package.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="django-odata",
    version="0.1.0",
    author="Muhammad Abdugafarov",
    author_email="iam.markjobs@gmail.com",
    description="Bringing OData Standards to Django - A comprehensive package implementing OData v4 specification for REST APIs with powerful querying capabilities and enterprise-grade functionality",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dev-muhammad/django-odata",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Django :: 5.1",
        "Framework :: Django :: 5.2",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Django>=4.2",
        "djangorestframework>=3.12.0",
        "drf-flex-fields>=1.0.0",
        "odata-query>=0.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-django>=4.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "isort>=5.0",
            "pip-audit>=2.6.0",
            "bandit[toml]>=1.7.0",
        ],
    },
)
