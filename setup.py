# /home/ubuntu/mtap_sdk/setup.py
from setuptools import setup, find_packages

# Read the contents of your README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mtap_sdk",
    version="0.1.0", # Initial development version
    author="Manus AI (Generated)",
    author_email="contact@example.com", # Placeholder
    description="SDK for the Memory Transfer and Access Protocol (MTAP)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/mtap_sdk", # Placeholder URL
    packages=find_packages(
        exclude=["tests", "tests.*", "examples", "examples.*"] # Exclude tests and examples from package
    ),
    classifiers=[
        "Development Status :: 3 - Alpha", # Alpha stage
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License", # Placeholder, confirm license
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.27.0,<0.29.0", # Specify a version range for httpx
        # Add other dependencies here if any were introduced
        # e.g., "pyjwt" for token handling if not done by auth_provider itself
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            # Add other development dependencies
        ]
    },
    project_urls={
        "Bug Tracker": "https://github.com/example/mtap_sdk/issues", # Placeholder
        "Documentation": "https://example.com/mtap_sdk_docs", # Placeholder
        "Source Code": "https://github.com/example/mtap_sdk", # Placeholder
    },
    include_package_data=True, # To include non-code files specified in MANIFEST.in (if any)
)

