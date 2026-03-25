
"""Vanna 2.0 wiring for the NL2SQL assignment.

This module keeps the Vanna 2.0 agent scaffold in one place so the app is
easy to read and easy to adapt for a real production deployment.

The project also includes a deterministic SQL fallback for portability:
- If Vanna and a supported LLM provider are configured, the agent is built.
- If not, the rest of the app still runs using the local SQL templates.

That gives you a runnable project even on a machine without API keys.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "clinic.db"
SEED_PATH = BASE_DIR / "memory_seed.json"


@dataclass
class VannaContext:
    db_path: Path
    seed_examples: list[dict[str, Any]]
    agent_memory: Any | None = None
    tool_registry: Any | None = None
    user_resolver: Any | None = None
    llm_service: Any | None = None
    agent: Any | None = None
    vanna_available: bool = False
    llm_provider: str = "fallback"


def load_seed_examples(path: Path = SEED_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [item for item in data if isinstance(item, dict) and "question" in item and "sql" in item]
    except json.JSONDecodeError:
        return []


def _import_vanna_components():
    try:
        from vanna import Agent, AgentConfig
        from vanna.core.registry import ToolRegistry
        from vanna.core.user import UserResolver, User, RequestContext
        from vanna.tools import RunSqlTool, VisualizeDataTool
        from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool
        from vanna.integrations.sqlite import SqliteRunner
        from vanna.integrations.local.agent_memory import DemoAgentMemory
        return {
            "Agent": Agent,
            "AgentConfig": AgentConfig,
            "ToolRegistry": ToolRegistry,
            "UserResolver": UserResolver,
            "User": User,
            "RequestContext": RequestContext,
            "RunSqlTool": RunSqlTool,
            "VisualizeDataTool": VisualizeDataTool,
            "SaveQuestionToolArgsTool": SaveQuestionToolArgsTool,
            "SearchSavedCorrectToolUsesTool": SearchSavedCorrectToolUsesTool,
            "SqliteRunner": SqliteRunner,
            "DemoAgentMemory": DemoAgentMemory,
        }
    except Exception:
        return None


class SimpleUserResolver:
    """Simple resolver that maps every request to the same default user."""

    async def resolve_user(self, request_context):  # type: ignore[override]
        try:
            email = request_context.get_cookie("vanna_email") or "guest@example.com"
        except Exception:
            email = "guest@example.com"
        return {
            "id": email,
            "username": "guest",
            "email": email,
            "permissions": [],
            "group_memberships": ["user"],
            "metadata": {"source": "simple_resolver"},
        }


def _build_llm_service():
    """
    Choose the LLM provider from environment variables.

    Priority:
      1. Google Gemini (GOOGLE_API_KEY)
      2. Groq (GROQ_API_KEY)
      3. Ollama local (OLLAMA_BASE_URL, default localhost)
    """
    provider_hint = (os.getenv("LLM_PROVIDER") or "").strip().lower()

    # Allow explicit provider selection when keys are available.
    if provider_hint in {"gemini", "google"} or (not provider_hint and os.getenv("GOOGLE_API_KEY")):
        try:
            from vanna.integrations.google import GeminiLlmService

            return GeminiLlmService(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                api_key=os.getenv("GOOGLE_API_KEY"),
            ), "gemini"
        except Exception:
            pass

    if provider_hint in {"groq", "openai"} or (not provider_hint and os.getenv("GROQ_API_KEY")):
        try:
            from vanna.integrations.openai import OpenAILlmService

            return OpenAILlmService(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                api_key=os.getenv("GROQ_API_KEY"),
                base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            ), "groq"
        except Exception:
            pass

    # Default to Ollama, which is fully local if the user has it installed.
    try:
        from vanna.integrations.openai import OpenAILlmService

        return OpenAILlmService(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ), "ollama"
    except Exception:
        return None, "fallback"


def _maybe_seed_agent_memory(agent_memory: Any, seed_examples: list[dict[str, Any]]) -> None:
    """
    Best-effort seeding for in-memory backends.

    Vanna's public docs show DemoAgentMemory as an in-memory store but the
    exact direct seeding API is intentionally avoided here because it can vary
    between releases. This helper tries a few likely method names and otherwise
    leaves the examples in memory_seed.json, which the app uses directly.
    """
    if agent_memory is None or not seed_examples:
        return

    candidate_methods = [
        "save_question_tool_args",
        "add",
        "add_item",
        "append",
        "save",
        "store",
        "insert",
    ]

    for example in seed_examples:
        question = example["question"]
        sql = example["sql"]
        payloads = [
            (question, "run_sql", {"sql": sql}),
            (question, {"tool_name": "run_sql", "args": {"sql": sql}}),
            (question, sql),
        ]
        saved = False
        for method_name in candidate_methods:
            method = getattr(agent_memory, method_name, None)
            if not callable(method):
                continue
            for payload in payloads:
                try:
                    method(*payload)  # type: ignore[misc]
                    saved = True
                    break
                except TypeError:
                    try:
                        method(payload)  # type: ignore[misc]
                        saved = True
                        break
                    except Exception:
                        continue
                except Exception:
                    continue
            if saved:
                break


def build_vanna_context(db_path: Path = DB_PATH) -> VannaContext:
    seeds = load_seed_examples()
    components = _import_vanna_components()
    if not components:
        return VannaContext(
            db_path=db_path,
            seed_examples=seeds,
            vanna_available=False,
        )

    llm_service, provider = _build_llm_service()
    if llm_service is None:
        # Keep the app runnable even without API keys or local LLM software.
        return VannaContext(
            db_path=db_path,
            seed_examples=seeds,
            vanna_available=False,
            llm_provider=provider,
        )

    ToolRegistry = components["ToolRegistry"]
    RunSqlTool = components["RunSqlTool"]
    VisualizeDataTool = components["VisualizeDataTool"]
    SaveQuestionToolArgsTool = components["SaveQuestionToolArgsTool"]
    SearchSavedCorrectToolUsesTool = components["SearchSavedCorrectToolUsesTool"]
    SqliteRunner = components["SqliteRunner"]
    DemoAgentMemory = components["DemoAgentMemory"]
    Agent = components["Agent"]
    AgentConfig = components["AgentConfig"]
    UserResolver = components["UserResolver"]
    User = components["User"]
    RequestContext = components["RequestContext"]

    class DefaultUserResolver(UserResolver):  # type: ignore[misc]
        async def resolve_user(self, request_context: RequestContext) -> User:
            email = request_context.get_cookie("vanna_email") or "guest@example.com"
            return User(
                id=email,
                username=email.split("@")[0],
                email=email,
                group_memberships=["user"],
                metadata={"source": "default_user_resolver"},
            )

    agent_memory = DemoAgentMemory(max_items=1000)
    _maybe_seed_agent_memory(agent_memory, seeds)

    tools = ToolRegistry()
    tools.register_local_tool(
        RunSqlTool(sql_runner=SqliteRunner(database_path=str(db_path))),
        access_groups=["user", "admin"],
    )
    tools.register_local_tool(VisualizeDataTool(), access_groups=["user", "admin"])
    tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=["admin"])
    tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=["user", "admin"])

    agent = Agent(
        llm_service=llm_service,
        tool_registry=tools,
        user_resolver=DefaultUserResolver(),
        agent_memory=agent_memory,
        config=AgentConfig(max_tool_iterations=8, stream_responses=False, temperature=0.2),
    )

    return VannaContext(
        db_path=db_path,
        seed_examples=seeds,
        agent_memory=agent_memory,
        tool_registry=tools,
        user_resolver=DefaultUserResolver(),
        llm_service=llm_service,
        agent=agent,
        vanna_available=True,
        llm_provider=provider,
    )


def get_runtime_context() -> VannaContext:
    return build_vanna_context()
