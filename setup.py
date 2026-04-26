from setuptools import setup, find_packages

setup(
    name="gumshoe-report",
    version="1.0.0",
    description="Automated insider threat triage — 24-hour user activity aggregator",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="you@yourorg.com",
    url="https://github.com/YOUR_USERNAME/gumshoe-report",
    license="MIT",
    python_requires=">=3.10",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "reportlab>=4.0.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "gumshoe=gumshoe:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: System :: Monitoring",
    ],
    keywords="insider threat, security, triage, UEBA, SIEM, DLP",
)
