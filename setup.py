from setuptools import setup, find_packages

setup(
    name="xcode-errors-mcp",
    version="1.0.0",
    description="MCP server for Xcode build errors and debug output integration",
    author="Xcode MCP Contributors",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "mcp>=1.0.0",
        "watchdog>=3.0.0",
        "regex>=2023.0.0",
        "python-dateutil>=2.8.0",
        "pyobjc-core>=10.0",
        "pyobjc-framework-Foundation>=10.0",
    ],
    entry_points={
        "console_scripts": [
            "xcode-mcp-server=xcode_mcp_server:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
