from omni_rpc.config.settings import Settings


class TestSettings:
    def test_defaults(self):
        settings = Settings({})
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        assert settings.workers == 1
        assert settings.reload is False
        assert settings.access_log is True
        assert settings.log_formatter == "standard"
        assert settings.log_handler == "stdout"

    def test_rate_limit_format(self):
        settings = Settings({"rate_limit": 120})
        assert settings.rate_limit == "120/minute"

    def test_api_overrides(self):
        settings = Settings(
            {
                "api": {
                    "host": "0.0.0.0",
                    "port": 9000,
                    "workers": 4,
                    "reload": True,
                    "access_log": False,
                }
            }
        )
        assert settings.host == "0.0.0.0"
        assert settings.port == 9000
        assert settings.workers == 4
        assert settings.reload is True
        assert settings.access_log is False

    def test_logging_overrides(self):
        settings = Settings(
            {
                "logging": {
                    "formatter": "json",
                    "handler": "stdout",
                    "levels": {"root": "DEBUG", "omni_rpc": "DEBUG"},
                }
            }
        )
        assert settings.log_formatter == "json"
        assert settings.log_levels["root"] == "DEBUG"

    def test_allowed_method_prefixes_default(self):
        settings = Settings({})
        assert settings.allowed_method_prefixes == {"eth", "net", "web3"}

    def test_allowed_method_prefixes_from_config(self):
        settings = Settings(
            {"rpc": {"allowed_method_prefixes": ["eth", "trace", "debug"]}}
        )
        assert settings.allowed_method_prefixes == {"eth", "trace", "debug"}

    def test_data_dir_and_chains_dir(self, tmp_path):
        settings = Settings({"data_dir": str(tmp_path)})
        assert settings.data_dir == tmp_path.resolve()
        assert settings.chains_dir == tmp_path.resolve() / "ethereum-lists/_data/chains"

    def test_log_config_structure(self):
        settings = Settings({"logging": {"formatter": "simple"}})
        config = settings.log_config
        assert config["version"] == 1
        assert "formatters" in config
        assert "handlers" in config
        assert "loggers" in config
