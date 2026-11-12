# FinSight AI

An enterprise-style multi-agent financial investigation platform built with Python, LangGraph, MCP, and evidence-grounded AI.

## Overview

FinSight AI is an engineering project exploring how autonomous AI agents can investigate unusual financial transactions, analyze account relationships, gather evidence, and generate structured investigation recommendations with human oversight.

The project uses synthetic financial data for development and testing.

## Planned Architecture

- **Supervisor Agent:** Coordinates investigation workflows.
- **Transaction Analysis Agent:** Investigates transaction patterns.
- **Entity Investigation Agent:** Explores relationships between accounts.
- **Policy Research Agent:** Retrieves relevant compliance policies.
- **Risk Assessment:** Generates evidence-backed recommendations.
- **Tool Execution Layer:** Provides validated and authorized tool execution.
- **Memory and State:** Supports persistent investigation state and recovery.

## Technology Stack

- Python
- LangGraph (planned)
- Model Context Protocol (MCP) (planned)
- FastAPI (planned)
- PostgreSQL (planned)
- Pydantic (planned)
- Pytest

## Current Development

- Synthetic customer, account, transaction, and investigation-alert datasets
- Initial transaction and relationship lookup tools
- Basic unit tests

## Generate Synthetic Data

```bash
python3 scripts/generate_data.py
```

## Run Tests

```bash
python -m pytest tests/ -v
```

## Roadmap

1. Synthetic dataset and initial tools
2. Tool Registry and Tool Gateway
3. LangGraph multi-agent orchestration
4. MCP tool integration
5. Persistent state and checkpointing
6. Evidence evaluation and dynamic replanning
7. Human-in-the-loop review
8. Observability, security, and evaluation

## Disclaimer

This project uses synthetic data and fictional investigation scenarios. It is intended for software engineering research and demonstration, not real-world financial compliance decisions.