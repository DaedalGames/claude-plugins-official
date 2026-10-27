"""The inner CLI runs on a handed claude.ai token, not a stored login."""
import llm

OAUTH_TOKEN = "sk-ant-oat01-token"


def _spawn_env(monkeypatch, **credentials):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    for name, value in credentials.items():
        monkeypatch.setenv(name, value)
    return llm._agentic_spawn_env()


class TestReviewerOauthToken:
    def test_claude_ai_token_goes_to_the_oauth_variable(self, monkeypatch):
        env = _spawn_env(monkeypatch, ANTHROPIC_AUTH_TOKEN=OAUTH_TOKEN)
        assert env["CLAUDE_CODE_OAUTH_TOKEN"] == OAUTH_TOKEN
        assert env["ANTHROPIC_AUTH_TOKEN"] == ""

    def test_cache_writes_stay_at_five_minutes(self, monkeypatch):
        env = _spawn_env(monkeypatch, ANTHROPIC_AUTH_TOKEN=OAUTH_TOKEN)
        assert env["FORCE_PROMPT_CACHING_5M"] == "1"

    def test_other_bearer_stays_where_it_was(self, monkeypatch):
        env = _spawn_env(monkeypatch, ANTHROPIC_AUTH_TOKEN="gateway-bearer")
        assert env["ANTHROPIC_AUTH_TOKEN"] == "gateway-bearer"
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in env

    def test_api_key_wins_over_a_claude_ai_token(self, monkeypatch):
        env = _spawn_env(monkeypatch, ANTHROPIC_API_KEY="key", ANTHROPIC_AUTH_TOKEN=OAUTH_TOKEN)
        assert env["ANTHROPIC_AUTH_TOKEN"] == ""
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in env

    def test_no_credential_adds_nothing(self, monkeypatch):
        env = _spawn_env(monkeypatch)
        assert env["ANTHROPIC_AUTH_TOKEN"] == ""
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in env
