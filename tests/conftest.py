import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_stub_modules() -> None:
    google = sys.modules.setdefault("google", types.ModuleType("google"))

    # Stub google.genai
    genai = types.ModuleType("google.genai")
    sys.modules.setdefault("google.genai", genai)
    google.genai = genai

    class DummyModels:
        def generate_content(self, *args, **kwargs):  # noqa: D401
            part = types.SimpleNamespace(text="{}", inline_data=None)
            content = types.SimpleNamespace(parts=[part])
            candidate = types.SimpleNamespace(content=content)
            return types.SimpleNamespace(candidates=[candidate])

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self.models = DummyModels()

    genai.Client = DummyClient

    genai_types = types.ModuleType("google.genai.types")

    class Content:
        def __init__(self, role=None, parts=None):
            self.role = role
            self.parts = parts or []

    class Part:
        def __init__(self, text=None, data=None, mime_type=None):
            self.text = text
            self.data = data
            self.mime_type = mime_type

        @classmethod
        def from_text(cls, text):
            return cls(text=text)

        @classmethod
        def from_bytes(cls, data, mime_type):
            return cls(data=data, mime_type=mime_type)

    class GenerateContentConfig:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    genai_types.Content = Content
    genai_types.Part = Part
    genai_types.GenerateContentConfig = GenerateContentConfig
    sys.modules.setdefault("google.genai.types", genai_types)
    genai.types = genai_types

    # Stub google.adk modules
    adk = sys.modules.setdefault("google.adk", types.ModuleType("google.adk"))
    google.adk = adk

    adk_agents = types.ModuleType("google.adk.agents")
    sys.modules.setdefault("google.adk.agents", adk_agents)
    adk.agents = adk_agents

    llm_agent = types.ModuleType("google.adk.agents.llm_agent")
    sys.modules.setdefault("google.adk.agents.llm_agent", llm_agent)
    adk_agents.llm_agent = llm_agent

    class DummyAgent:
        def __init__(self, *args, **kwargs):
            pass

    llm_agent.Agent = DummyAgent

    runners = types.ModuleType("google.adk.runners")
    sys.modules.setdefault("google.adk.runners", runners)
    adk.runners = runners

    class DummyRunner:
        def __init__(self, *args, **kwargs):
            pass

        def run_async(self, *args, **kwargs):
            async def _empty():
                if False:
                    yield None

            return _empty()

    runners.Runner = DummyRunner

    sessions = types.ModuleType("google.adk.sessions")
    sys.modules.setdefault("google.adk.sessions", sessions)
    adk.sessions = sessions

    class DummySessionService:
        async def create_session(self, *args, **kwargs):
            return object()

    sessions.InMemorySessionService = DummySessionService

    tools = types.ModuleType("google.adk.tools")
    sys.modules.setdefault("google.adk.tools", tools)
    adk.tools = tools

    function_tool = types.ModuleType("google.adk.tools.function_tool")
    sys.modules.setdefault("google.adk.tools.function_tool", function_tool)
    tools.function_tool = function_tool

    class FunctionTool:
        def __init__(self, func):
            self.func = func

    function_tool.FunctionTool = FunctionTool


_ensure_stub_modules()

import skillbuddy.config as config


@pytest.fixture(autouse=True)
def configure_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("SERPAPI_KEY", "test-serpapi-key")
    config.set_google_api_key("test-google-key")
    config.set_serpapi_key("test-serpapi-key")
    yield
    config.set_google_api_key(None)
    config.set_serpapi_key(None)
