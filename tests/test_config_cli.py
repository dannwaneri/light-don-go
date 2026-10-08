import pytest

from light_don_go import cli, config


def test_help_lists_three_subcommands(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    for c in ("watch", "simulate", "refresh"):
        assert c in out


def test_missing_config_uses_port_harcourt_defaults(tmp_path):
    cfg = config.load(tmp_path / "nope.toml")
    assert (cfg.lat, cfg.lon, cfg.place_name) == (4.8156, 7.0498, "Port Harcourt")
    assert cfg.naira_saved_per_hour == 1500


def test_bad_lat_is_a_clear_error(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("lat = 123\nlon = 7.0\n")
    with pytest.raises(config.ConfigError, match="lat must be between"):
        config.load(p)


def test_fuel_values_absent_from_file_drop_the_fuel_fact(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("lat = 4.8\nlon = 7.0\n")
    assert config.load(p).naira_saved_per_hour is None


def test_repo_config_loads():
    cfg = config.load("config.toml")
    assert cfg.model == "gemma4:e2b-it-qat" and cfg.naira_saved_per_hour == 1500
