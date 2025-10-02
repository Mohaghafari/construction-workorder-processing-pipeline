from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="construction-workorder-pipeline",
    version="1.0.0",
    author="Mohammad Ghafari",
    author_email="mohaghafari@example.com",
    description="Production-grade AI data pipeline for construction work order processing with OCR, ML, and data warehousing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Mohaghafari/construction-workorder-processing-pipeline",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "work-order-pipeline=scripts.run_pipeline:main",
        ],
    },
)
