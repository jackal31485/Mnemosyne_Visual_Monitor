# Add the bootstrap script.
#!/usr/bin/env python3
import pathlib
from src.domain.collective import CollectiveDAO, DB_PATH

if __name__ == "__main__":
    dao = CollectiveDAO()
    dao.ensure_schema()
    print(f"Collective database initialized at {DB_PATH}")
