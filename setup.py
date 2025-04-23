from setuptools import setup, find_packages

setup(
    name="logflow",
    version="0.1.0",
    description="Forward logs as JSON over UDP, with CLI and Python logging handler.",
    author="Your Name",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "logflow=logflow.cli:main",
            "logflow-listener=logflow.listener:main_entrypoint",
        ],
    },
    python_requires=">=3.7",
    install_requires=[],
)
