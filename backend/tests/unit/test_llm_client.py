import pytest
from app.llm.llm_client import MockLLMClient, OpenAILLMClient
from app.api.v1.deps import get_llm_client
from app.core.exceptions import ConfigurationError

@pytest.mark.asyncio
async def test_mock_llm_client_generate():
    client = MockLLMClient(mock_response="Hello world")
    response = await client.generate([{"role": "user", "content": "Hi"}])
    assert response == "Hello world"

@pytest.mark.asyncio
async def test_mock_llm_client_stream():
    client = MockLLMClient(mock_response="Hello world")
    chunks = []
    async for chunk in client.stream([{"role": "user", "content": "Hi"}]):
        chunks.append(chunk)
    
    # The mock currently splits by space and appends space
    assert chunks == ["Hello ", "world "]
    assert "".join(chunks) == "Hello world "

def test_get_llm_client_mock_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    import app.core.config
    app.core.config.get_settings.cache_clear()
    
    client = get_llm_client()
    assert isinstance(client, MockLLMClient)

def test_get_llm_client_with_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    
    # We must bust the lru_cache for get_settings in tests to reflect monkeypatch
    import app.core.config
    app.core.config.get_settings.cache_clear()
    
    client = get_llm_client()
    assert isinstance(client, OpenAILLMClient)
    assert client.model == "test-model"
    # AsyncOpenAI client internal api_key check
    assert client.client.api_key == "test-key"

def test_get_llm_client_missing_api_key(monkeypatch):
    # Ensure it's not set
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "")
    
    import app.core.config
    app.core.config.get_settings.cache_clear()
    
    client = get_llm_client()
    assert client is None

def test_get_llm_client_unsupported_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    import app.core.config
    app.core.config.get_settings.cache_clear()
    
    with pytest.raises(ConfigurationError):
        get_llm_client()

def test_openai_llm_client_init():
    client = OpenAILLMClient(api_key="test", model="gpt-4o", base_url="https://custom.com/v1")
    assert client.model == "gpt-4o"
    assert client.client.base_url == "https://custom.com/v1/"
