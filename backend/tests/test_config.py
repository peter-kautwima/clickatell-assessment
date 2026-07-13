"""Settings regression tests: backend/.env must load regardless of the
directory uvicorn is started from (both README options are equivalent).
"""

from pathlib import Path

from app.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_env_file_is_anchored_to_backend_dir_not_cwd():
    env_file = Path(Settings.model_config["env_file"])

    assert env_file.is_absolute()
    assert env_file == BACKEND_DIR / ".env"
