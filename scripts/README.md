# Scripts - 工具脚本

This directory contains utility scripts for the Inty backend.

## compress_agent_avatar_image.py

Compresses PNG avatar images to JPEG format and updates the database records.

### Usage

```bash
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://user:password@host:port/database"
```

### Options

- `--pg_url`: PostgreSQL connection URL (required)
- `--quality`: JPEG compression quality 1-100 (default: 80)

### What it does

1. Connects to PostgreSQL database using the provided URL
2. Queries the `agents` table for records with PNG avatar URLs
3. Downloads each PNG image
4. Compresses PNG to JPEG with specified quality
5. Uploads JPEG to Google Cloud Storage in the same directory structure
6. Updates the database record with the new JPEG URL
7. Generates detailed logs of the process

### Requirements

- Valid `config.yaml` with GCS credentials configured
- PostgreSQL database access
- Internet access to download images
- PIL (Pillow) for image processing

### Example

```bash
# Compress with default quality (80)
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://postgres:password@localhost:5432/inty_db"

# Compress with custom quality
python scripts/compress_agent_avatar_image.py --pg_url "postgresql://postgres:password@localhost:5432/inty_db" --quality 90
```
