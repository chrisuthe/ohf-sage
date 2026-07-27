from pathlib import Path
from ohf_principles.config import load_config, authorities_for


def test_load_config_reads_repos_and_defaults(tmp_path):
    cfg_file = tmp_path / "sources.yaml"
    cfg_file.write_text(
        "global_authorities: [marcelveldt]\n"
        "repos:\n"
        "  - repo: music-assistant/server\n"
        "    authorities: [MarvinSchenkel]\n",
        encoding="utf-8",
    )
    config = load_config(cfg_file)
    assert config["global_authorities"] == ["marcelveldt"]
    assert config["repos"][0]["repo"] == "music-assistant/server"
    assert isinstance(config["defaults"], dict)  # defaulted when absent


def test_authorities_for_merges_global_and_local_lowercased():
    config = {"global_authorities": ["marcelveldt"], "repos": []}
    repo_cfg = {"repo": "music-assistant/server", "authorities": ["MarvinSchenkel"]}
    assert authorities_for(repo_cfg, config) == {"marcelveldt", "marvinschenkel"}


def test_load_config_rejects_missing_repos(tmp_path):
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("global_authorities: [marcelveldt]\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError):
        load_config(cfg_file)
