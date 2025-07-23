#!/usr/bin/env python3
"""
Setup script for TimeNIC Manager
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="timenic-manager",
    version="1.0.0",
    author="TimeNIC Team",
    description="Comprehensive management solution for TimeNIC PCIe cards",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-repo/timenic-manager",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Hardware",
        "Topic :: System :: Networking :: Time Synchronization",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "PyQt6>=6.4.0",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
        "websockets>=12.0",
    ],
    entry_points={
        "console_scripts": [
            "timenic-cli=cli.timenic_cli:cli",
            "timenic-gui=gui.timenic_gui:main",
            "timenic-web=web.backend.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.html", "*.css", "*.js"],
    },
)