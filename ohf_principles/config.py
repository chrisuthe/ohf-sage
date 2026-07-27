from pathlib import Path
import yaml


def load_config(path):
    """Load and lightly validate the sources.yaml config."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data.get("repos"), list):
        raise ValueError("config must contain a 'repos' list")
    data.setdefault("global_authorities", [])
    data.setdefault("defaults", {})
    return data


def authorities_for(repo_cfg, config):
    """Set of authoritative logins for a repo (globals + per-repo), lowercased."""
    merged = list(config.get("global_authorities", [])) + list(repo_cfg.get("authorities", []))
    return {login.lower() for login in merged}
