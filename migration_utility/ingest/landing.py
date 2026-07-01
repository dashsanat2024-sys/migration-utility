from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from migration_utility.config import get_settings


def get_landing_root() -> Path:
    settings = get_settings()
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        root = Path("/tmp/migration-utility/landing")
    else:
        root = Path(settings.landing_zone_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def project_landing_dir(project_slug: str) -> Path:
    path = get_landing_root() / project_slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(project_slug: str, original_filename: str, src_path: Path) -> Path:
    dest_dir = project_landing_dir(project_slug)
    dest = dest_dir / f"{uuid.uuid4()}_{original_filename}"
    shutil.copy2(src_path, dest)
    return dest
