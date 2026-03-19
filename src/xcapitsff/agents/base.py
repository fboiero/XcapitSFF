"""Base agent runtime — connects business agents to Anthropic API."""

from dataclasses import dataclass, field

import anthropic

from xcapitsff.config import settings


@dataclass
class AgentMessage:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class AgentResult:
    response: str
    model: str
    usage: dict = field(default_factory=dict)


class BaseAgent:
    """Base class for all business agents."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.conversation: list[AgentMessage] = []

    def run(self, user_input: str) -> AgentResult:
        """Run the agent with user input and return the response."""
        self.conversation.append(AgentMessage(role="user", content=user_input))

        messages = [{"role": m.role, "content": m.content} for m in self.conversation]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=messages,
        )

        assistant_text = response.content[0].text
        self.conversation.append(AgentMessage(role="assistant", content=assistant_text))

        return AgentResult(
            response=assistant_text,
            model=self.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    def reset(self) -> None:
        """Clear conversation history."""
        self.conversation = []
