# a_kp_mcp-project

## Overview
Professional learning project for **Model Context Protocol (MCP)** — building a production-grade MCP server with database integration to understand how MCP extends LLM context with dynamic data sources.

## Project Goals
- Master MCP architecture: client-server model, transports, and primitives (Resources, Tools, Prompts)
- Build a functional MCP server in Python that exposes database operations
- Implement best practices: type hints, testing, logging, error handling
- Create comprehensive documentation with architecture diagrams
- Demonstrate real-world MCP use cases

## Tech Stack
- **Language**: Python 3.10+
- **MCP SDK**: `mcp` (official Python SDK)
- **Database**: SQLite (local development)
- **ORM**: SQLAlchemy 2.0
- **CLI**: Click
- **Testing**: pytest with async support
- **Code Quality**: Black, Ruff, MyPy

## Project Structure
```
a_kp_mcp-project/
├── src/                 # Source code
│   ├── server/         # MCP server implementation
│   ├── client/         # MCP client for testing
│   └── database/       # Database models and connections
├── tests/              # Unit and integration tests
├── docs/               # Documentation and diagrams
├── data/               # Database files and seed data
├── config/             # Configuration files
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Quick Start
```powershell
# Clone and setup
cd a_kp_mcp-project
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Initialize database
python src/database/init_db.py

# Run MCP server
python src/server/main.py

# Test with client
python src/client/test_client.py
```

## Learning Path
1. ✅ Project setup and dependencies
2. 🔄 Database schema design and seed data
3. 📚 MCP fundamentals research
4. 🏗️ MCP server implementation
5. 🔌 Client integration and testing
6. 📝 Documentation and diagrams
7. 🚀 GitHub repository and summary

## Author
- GitHub: [@amittian](https://github.com/amittian)
- Project: MCP Learning Initiative

## License
MIT License - see LICENSE file for details

---
*Built with GitHub Copilot and professional development practices*
