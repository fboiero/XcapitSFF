"""Argentor Client — HTTP bridge to the Argentor agent runtime.

XcapitSFF delegates all AI agent execution to Argentor (Rust) via HTTP.
This replaces the direct Anthropic API calls with calls to Argentor's
gateway, which provides: 14 LLM backends, circuit breaker, failover,
WASM sandboxing, compliance audit trail, and token budgeting.

When Argentor is not available, falls back to dry-run mode.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from xcapitsff.config import settings

logger = logging.getLogger(__name__)

ARGENTOR_DEFAULT_URL = "http://localhost:3000"


@dataclass
class ArgentorConfig:
    base_url: str = ARGENTOR_DEFAULT_URL
    api_key: str = ""
    timeout: float = 30.0
    retries: int = 2


@dataclass
class AgentResponse:
    """Response from Argentor agent execution."""
    content: str
    session_id: str | None = None
    model_used: str | None = None
    tokens_input: int = 0
    tokens_output: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    duration_ms: float = 0
    success: bool = True
    error: str | None = None
    compliance_flags: list[str] = field(default_factory=list)


class ArgentorClient:
    """HTTP client for communicating with the Argentor gateway."""

    def __init__(self, config: ArgentorConfig | None = None):
        self.config = config or ArgentorConfig(
            base_url=getattr(settings, "argentor_url", ARGENTOR_DEFAULT_URL),
            api_key=getattr(settings, "argentor_api_key", ""),
        )
        self._available: bool | None = None
        self._last_health_check: datetime | None = None

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def health_check(self) -> bool:
        """Check if Argentor gateway is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.config.base_url}/api/v1/metrics",
                    headers=self._headers(),
                )
                self._available = resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            self._available = False
        self._last_health_check = datetime.now()
        return self._available

    async def is_available(self) -> bool:
        """Check availability with caching (re-check every 60s)."""
        if self._available is None or (
            self._last_health_check
            and (datetime.now() - self._last_health_check).total_seconds() > 60
        ):
            return await self.health_check()
        return self._available

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> AgentResponse:
        """Send a chat message to an Argentor agent.

        This is the primary interface. XcapitSFF sends business context,
        Argentor handles the LLM execution with all its infra.
        """
        if not await self.is_available():
            return self._dry_run_response(message)

        payload = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                start = datetime.now()
                resp = await client.post(
                    f"{self.config.base_url}/api/v1/agent/chat",
                    json=payload,
                    headers=self._headers(),
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code != 200:
                    return AgentResponse(
                        content="",
                        success=False,
                        error=f"Argentor returned {resp.status_code}: {resp.text[:200]}",
                        duration_ms=duration,
                    )

                data = resp.json()
                return AgentResponse(
                    content=data.get("response", data.get("content", "")),
                    session_id=data.get("session_id"),
                    model_used=data.get("model"),
                    tokens_input=data.get("tokens_input", 0),
                    tokens_output=data.get("tokens_output", 0),
                    tool_calls=data.get("tool_calls", []),
                    duration_ms=duration,
                    success=True,
                    compliance_flags=data.get("compliance_flags", []),
                )

        except httpx.TimeoutException:
            return AgentResponse(
                content="", success=False,
                error=f"Argentor timeout after {self.config.timeout}s",
            )
        except httpx.ConnectError:
            self._available = False
            return self._dry_run_response(message)
        except Exception as e:
            return AgentResponse(
                content="", success=False, error=f"Argentor error: {str(e)}",
            )

    async def get_sessions(self) -> list[dict]:
        """List active sessions in Argentor."""
        if not await self.is_available():
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.config.base_url}/api/v1/sessions",
                    headers=self._headers(),
                )
                return resp.json() if resp.status_code == 200 else []
        except Exception:
            return []

    async def get_skills(self) -> list[dict]:
        """List available skills in Argentor."""
        if not await self.is_available():
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.config.base_url}/api/v1/skills",
                    headers=self._headers(),
                )
                return resp.json() if resp.status_code == 200 else []
        except Exception:
            return []

    async def get_metrics(self) -> dict:
        """Get Argentor metrics."""
        if not await self.is_available():
            return {"status": "unavailable"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.config.base_url}/api/v1/metrics",
                    headers=self._headers(),
                )
                return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {"status": "error"}

    def _dry_run_response(self, message: str) -> AgentResponse:
        """Fallback when Argentor is not available."""
        logger.warning("Argentor unavailable — returning dry-run response")
        return AgentResponse(
            content=(
                f"[ARGENTOR OFFLINE] Agent runtime not available. "
                f"Start Argentor with: cd Argentor && cargo run -- serve\n\n"
                f"Received message ({len(message)} chars): {message[:100]}..."
            ),
            success=True,  # don't block business logic
            error="argentor_unavailable",
        )

    def get_status(self) -> dict:
        return {
            "base_url": self.config.base_url,
            "available": self._available,
            "last_check": self._last_health_check.isoformat() if self._last_health_check else None,
        }


# Singleton
argentor_client = ArgentorClient()
