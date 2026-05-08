import os
from pathlib import Path


ENV_FILENAMES = (".env", ".env.local")


def _parse_env_line(line):
    text = (line or "").strip()
    if not text or text.startswith("#"):
        return "", ""

    if text.startswith("export "):
        text = text[7:].strip()

    if "=" not in text:
        return "", ""

    key, value = text.split("=", 1)
    key = key.strip()
    value = value.strip()

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]

    return key, value


def load_env_files(base_dir=None, override=False):
    project_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
    loaded_files = []

    for filename in ENV_FILENAMES:
        env_path = project_dir / filename
        if not env_path.exists() or not env_path.is_file():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            key, value = _parse_env_line(raw_line)
            if not key:
                continue
            if override or key not in os.environ:
                os.environ[key] = value

        loaded_files.append(str(env_path))

    return loaded_files
