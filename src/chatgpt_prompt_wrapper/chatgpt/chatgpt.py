from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from typing import Any, cast

import openai
import tiktoken
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from ..chatgpt_prompt_wrapper_exception import ChatGPTPromptWrapperError

Message = dict[str, Any]
Messages = list[Message]


@dataclass
class ChatGPT:
    """ChatGPT class for interacting with OpenAI's API.

    Parameters
    ----------
    key : str
        OpenAI API key.
    model : str
        The model to use.
    max_tokens : int
        The maximum number of tokens to generate in the chat completion. Set 0 to use the max values for the model.
    min_max_tokens: int
        The minimum of max_tokens for the completion when max_tokens = 0.
    tokens_limit : int
        The limit of the total tokens of the prompt and the completion. Set 0 to use the max values for the model.
    temperature: float
        Sampling temperature (0 ~ 2).
    top_p: float
        Probability (0 ~ 1) that the model will consider the top_p tokens. Do not set both temperature and top_p in the same time.
    presence_penalty: float
        The penalty for the model to return the same token (-2 ~ 2).
    frequency_penalty: float
        The penalty for the model to return the same token multiple times (-2 ~ 2).
    colors: dict[str, str]
        The colors to use for the different names/roles.
    alias: dict[str, str]
        The aliases of role names.
    model_context_window : dict[str, int]
        The context window for each model.
    model_max_tokens: dict[str, int]
        The maximum tokens for each model.
    prices: dict[str, tuple[float, float]]
        The prices for each model.
    encoding_name: str
        Encoding name for tiktoken. If not specified, the encoding is decided by the model name.

    """

    key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 0
    min_max_tokens: int = 200
    tokens_limit: int = 0
    temperature: float = 1
    top_p: float = 1
    presence_penalty: float = 0
    frequency_penalty: float = 0
    colors: dict[str, str] = field(
        default_factory=lambda: {
            "system": "blue",
            "user": "green",
            "assistant": "cyan",
        },
    )
    alias: dict[str, str] = field(
        default_factory=lambda: {
            "system": "System",
            "user": "User",
            "assistant": "Assistant",
        },
    )
    model_context_window: dict[str, int] = field(default_factory=dict)
    model_max_tokens: dict[str, int] = field(default_factory=dict)
    prices: dict[str, tuple[float, float]] = field(default_factory=dict)
    encoding_name: str = ""

    def __post_init__(self) -> None:
        self.log = logging.getLogger(__name__)
        self.client = openai.OpenAI(api_key=self.key)
        if self.max_tokens:
            self.min_max_tokens = self.max_tokens

        self.ansi_colors = {
            "black": "30",
            "red": "31",
            "green": "32",
            "yellow": "33",
            "blue": "34",
            "purple": "35",
            "cyan": "36",
            "gray": "37",
        }

        # Ref: https://platform.openai.com/docs/models/overview
        self.model_context_window.update(
            {
                k: v
                for k, v in {
                    "gpt-4o": 128000,
                    "gpt-4o-mini": 128000,
                    "gpt-4-turbo": 128000,
                    "gpt-4": 8192,
                    "gpt-3.5-turbo": 16385,
                }.items()
                if k not in self.model_context_window
            },
        )
        self.model_max_tokens.update(
            {
                k: v
                for k, v in {
                    "gpt-4o": 4096,
                    "gpt-4o-mini": 16384,
                    "gpt-4-turbo": 4096,
                    "gpt-4": 8192,
                    "gpt-3.5-turbo": 4096,
                }.items()
                if k not in self.model_max_tokens
            },
        )

        # prices / 1K tokens in USD, (Prompt, Completion)
        # Ref: https://openai.com/pricing#language-models
        self.prices.update(
            {
                k: v
                for k, v in {
                    "gpt-4o": (0.005, 0.015),
                    "gpt-4o-mini": (0.00015, 0.0006),
                    "gpt-4-turbo": (0.010, 0.030),
                    "gpt-4": (0.030, 0.060),
                    "gpt-3.5-turbo": (0.003, 0.006),
                }.items()
                if k not in self.prices
            },
        )

        self.set_model(self.model)

        for k, v in self.alias.items():
            if v not in self.colors and k in self.colors:
                self.colors[v] = self.colors[k]

    def set_model(self, model: str) -> None:
        self.model = self.model
        # Total number of tokens must be maximum tokens for model - 1
        if self.tokens_limit == 0:
            self.tokens_limit = self.model_max_tokens[self.model] - 1
        else:
            self.tokens_limit = min(
                self.tokens_limit,
                self.model_max_tokens[self.model] - 1,
            )
        self.prepare_tokens_checker()

    def prepare_tokens_checker(self) -> None:
        # https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
        if self.encoding_name:
            self.encoding = tiktoken.get_encoding(self.encoding_name)
        else:
            self.encoding = tiktoken.encoding_for_model(self.model)
        if self.model == "gpt-3.5-turbo-0301":
            self.tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            self.tokens_per_name = -1  # if there's a name, the role is omitted
        else:
            self.tokens_per_message = 3
            self.tokens_per_name = 1

        # every reply is primed with <|start|>assistant<|message|>
        self.reply_tokens = 3

    def add_color(self, text: str, name: str) -> str:
        if (
            sys.stdout.isatty()
            and name in self.colors
            and self.colors[name] in self.ansi_colors
        ):
            text = f"\033[{self.ansi_colors[self.colors[name]]};1m{text}\033[m"
        return text

    def check_prompt_tokens(self, prompt_tokens: int) -> None:
        if prompt_tokens + self.min_max_tokens > self.tokens_limit:
            raise ChatGPTPromptWrapperError(
                f"Too much tokens: prompt tokens ({prompt_tokens}) + completion tokens ({self.min_max_tokens}) > tokens limit ({self.tokens_limit}).",
            )

    # Ref: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    def num_tokens_from_message(
        self,
        message: Message,
        only_content: bool = False,
    ) -> int:
        if only_content:
            return len(self.encoding.encode(message["content"]))

        num_tokens = self.tokens_per_message
        for key, value in message.items():
            num_tokens += len(self.encoding.encode(value))
            if key == "name":
                num_tokens += self.tokens_per_name
        return num_tokens

    def num_total_tokens(self, prompt_tokens: int) -> int:
        return prompt_tokens + self.reply_tokens

    def num_tokens_from_messages(self, messages: Messages) -> int:
        num_tokens = 0
        for message in messages:
            num_tokens += self.num_tokens_from_message(message)
        return self.num_total_tokens(num_tokens)

    def get_max_tokens(self, messages: Messages) -> int:
        prompt_tokens = self.num_tokens_from_messages(messages)
        self.check_prompt_tokens(prompt_tokens)
        remain_tokens = self.tokens_limit - prompt_tokens
        if self.max_tokens:
            return min(self.max_tokens, remain_tokens)
        return max(self.min_max_tokens, remain_tokens)

    def fix_messages(self, messages: Messages) -> Messages:
        if "gpt-3.5" in self.model:
            for message in messages:
                if message["role"] == "system":
                    message["role"] = "user"
        return messages

    def get_name(self, message: dict[str, str]) -> str:
        if "name" in message:
            name = message["name"]
        else:
            name = self.alias.get(message["role"], message["role"])
        return name

    def get_output(
        self,
        message: Message,
        size: int = 0,
        add_linebreak: bool = False,
    ) -> str:
        name = self.get_name(message)
        name = self.add_color(f"{name:>{size}}", name)
        lb = "\n" if add_linebreak else ""
        return f"{name}> {message['content']}{lb}"

    def completion(
        self,
        messages: Messages,
        stream: bool = False,
    ) -> ChatCompletion | openai.Stream[ChatCompletionChunk]:
        max_tokens = self.get_max_tokens(messages)

        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore
            max_tokens=max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            stream=stream,
        )

    def completion_message(self, messages: Messages) -> ChatCompletion:
        return cast(ChatCompletion, self.completion(messages, stream=False))

    def completion_stream(
        self,
        messages: Messages,
    ) -> openai.Stream[ChatCompletionChunk]:
        return cast(
            openai.Stream[ChatCompletionChunk],
            self.completion(messages, stream=True),
        )

    def run(self, messages: Messages) -> float:
        return 0
