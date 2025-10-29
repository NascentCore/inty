# Agent Management Scripts - 角色管理脚本

## copy_agent.py

Copy an agent from one PostgreSQL database to another.

### Usage

```bash
python copy_agent.py --name "Amber" \
  --source-pg "postgresql://user:pass@host:port/db" \
  --dest-pg "postgresql://user:pass@host:port/db"
```

### Options

- `--name`: Name of the agent to copy (required)
- `--source-pg`: Source PostgreSQL URL (required)
- `--dest-pg`: Destination PostgreSQL URL (required)
- `--force`: Overwrite if agent already exists in destination (optional)

### Examples

```bash
# Copy agent from dev to production
python copy_agent.py --name "Amber" \
  --source-pg "postgresql://postgres:sxwl666!@localhost:15432/devdb" \
  --dest-pg "postgresql://postgres:sxwl666!@localhost:5432/inty"

# Copy with force overwrite
python copy_agent.py --name "Amber" --force \
  --source-pg "postgresql://postgres:sxwl666!@localhost:15432/devdb" \
  --dest-pg "postgresql://postgres:sxwl666!@localhost:5432/inty"
```

### Notes

- The script uses SQLAlchemy with async sessions for database operations
- All agent fields are copied including character card data, settings, etc.
- The script checks for existing agents in the destination database
- Use `--force` flag to overwrite existing agents
