from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from typing import Any, Generator, cast

import openai
import tiktoken

from .chatgpt_prompt_wrapper_exception import ChatGPTPromptWrapperError

Messages = list[dict[str, str]]


# Ref: https://platform.openai.com/docs/models/overview
model_max_tokens = {
    "gpt-4": 8192,
    "gpt-4-0314": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-32k-0314": 32768,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-0301": 4096,
}

# prices / 1K tokens in USD, (Prompt, Completion)
# Ref: https://openai.com/pricing#language-models
prices = {
    "gpt-4": (0.03, 0.06),
    "gpt-4-0314": (0.03, 0.06),
    "gpt-4-32k": (0.06, 0.12),
    "gpt-4-32k-0314": (0.06, 0.12),
    "gpt-3.5-turbo": (0.002, 0.002),
    "gpt-3.5-turbo-0301": (0.002, 0.002),
}


# Ref: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
def num_tokens_from_message(
    message: dict[str, str], model: str, only_content: bool = False
) -> int:
    encoding = tiktoken.encoding_for_model(model)
    if "gpt-3.5" in model:
        # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_message = 4
        # if there's a name, the role is omitted
        tokens_per_name = -1
    elif "gpt-4" in model:
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise ChatGPTPromptWrapperError(f"Model: {model} is not supported.")

    if only_content:
        return len(encoding.encode(message["content"]))

    num_tokens = tokens_per_message
    for key, value in message.items():
        num_tokens += len(encoding.encode(value))
        if key == "name":
            num_tokens += tokens_per_name
    return num_tokens


def num_total_tokens(prompt_tokens: int, model: str) -> int:
    return prompt_tokens + 3


def num_tokens_from_messages(messages: Messages, model: str) -> int:
    num_tokens = 0
    for message in messages:
        num_tokens += num_tokens_from_message(message, model)
    # every reply is primed with <|start|>assistant<|message|>
    return num_total_tokens(num_tokens, model)


@dataclass
class ChatGPT:
    """ChatGPT class for interacting with OpenAI's API.

    Parameters
    ----------
    key : str
        OpenAI API key.
    show: bool
        Whether to show the prompt.
    model : str
        The model to use.
    max_tokens : int
        The maximum number of tokens to generate in the chat completion. Set 0 to use the max values for the model minus prompt tokens.
    temperature: float
        Sampling temperature (0 ~ 2).
    top_p: float
        Probability (0 ~ 1) that the model will consider the top_p tokens. Do not set both temperature and top_p in the same time.
    presence_penalty: float
        The penalty for the model to return the same token (-2 ~ 2).
    frequency_penalty: float
        The penalty for the model to return the same token multiple times (-2 ~ 2).
    chat_exit_cmd: list[str]
        The command to exit the chat.
    """

    key: str
    show: bool = False
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 0
    temperature: float = 1
    top_p: float = 1
    presence_penalty: float = 0
    frequency_penalty: float = 0
    colors: dict[str, int] = field(
        default_factory=lambda: {
            "system": 34,
            "user": 32,
            "assistant": 36,
        }
    )
    chat_exit_cmd: list[str] = field(
        default_factory=lambda: ["exit", "quit", "bye", "bye!"]
    )

    def __post_init__(self) -> None:
        self.log = logging.getLogger(__name__)
        openai.api_key = self.key

    def add_color(self, text: str, role: str, size: int = 0) -> str:
        if sys.stdout.isatty() and role in self.colors:
            text = f"\033[{self.colors[role]};1m{role:>{size}}\033[m"
        return text

    def check_prompt_tokens(self, prompt_tokens: int) -> None:
        if prompt_tokens >= model_max_tokens[self.model] - self.max_tokens:
            raise ChatGPTPromptWrapperError(
                f"Too much tokens: prompt tokens ({prompt_tokens}) >= model's max tokens ({model_max_tokens[self.model]}) - max_tokens for completion ({self.max_tokens})."
            )

    def get_max_tokens(self, messages: Messages) -> int:
        prompt_tokens = num_tokens_from_messages(messages, self.model)
        self.check_prompt_tokens(prompt_tokens)

        if self.max_tokens == 0:
            # it must be maximum tokens for model - 1
            max_tokens = model_max_tokens[self.model] - prompt_tokens - 1
        else:
            max_tokens = self.max_tokens
        return max_tokens

    def fix_messages(self, messages: Messages) -> Messages:
        if "gpt-3.5" in self.model:
            for message in messages:
                if message["role"] == "system":
                    message["role"] = "user"
        return messages

    def completion(
        self, messages: Messages, stream: bool = False
    ) -> Generator[dict[str, Any], None, None] | dict[str, Any]:
        max_tokens = self.get_max_tokens(messages)

        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            stream=stream,
        )
        return response

    def get_name(self, message: dict[str, str]) -> str:
        name = message["role"]
        if "name" in message:
            if "gpt-3.5" in self.model:
                name = message["name"]
            else:
                name = f"{message['name']} ({message['role']})"
        return name

    def get_output(self, message: dict[str, str], size: int = 0) -> str:
        name = self.add_color(self.get_name(message), message["role"], size)
        return f"{name}> {message['content']}"

    def ask(self, messages: Messages) -> float:
        messages = self.fix_messages(messages)
        max_size = max(
            10, max(len(self.get_name(message)) for message in messages)
        )
        if self.show:
            for message in messages:
                self.log.info(self.get_output(message, max_size))
        response = cast(
            dict[str, Any], self.completion(messages, stream=False)
        )

        finish_reason = response["choices"][0]["finish_reason"]
        if finish_reason == "stop":
            pass
        elif finish_reason == "length":
            usage = response["usage"]
            usage["prompt_tokens"], usage["completion_tokens"]
            self.log.warning(
                f'Too much tokens: prompt tokens = {response["usage"]["prompt_tokens"]}, completion tokens = {response["usage"]["completion_tokens"]}, while max_tokens = {self.max_tokens}, model\'s max tokens is {model_max_tokens[self.model]}.'
            )
        elif finish_reason == "content_filter":
            self.log.warning(
                "Omitted content due to a flag from the content filters."
            )
        elif finish_reason is None:
            self.log.warning("API response is incomplete")
        else:
            raise ChatGPTPromptWrapperError(
                f"Unknown finish_reason: {response['choices'][0]['finish_reason']}"
            )
        if self.show:
            answer = self.get_output(
                response["choices"][0]["message"], max_size
            )
        else:
            answer = response["choices"][0]["message"]["content"]
        self.log.info(answer)

        return (
            prices[self.model][0] * response["usage"]["prompt_tokens"] / 1000.0
            + prices[self.model][1]
            * response["usage"]["completion_tokens"]
            / 1000.0
        )

    def set_no_line_break_log(self) -> None:
        self.default_terminators = [
            (h, h.terminator)
            for h in self.log.handlers
            if isinstance(h, logging.StreamHandler)
        ]
        if self.log.parent:
            self.default_terminators += [
                (h, h.terminator)
                for h in self.log.parent.handlers
                if isinstance(h, logging.StreamHandler)
            ]
        for handler, _ in self.default_terminators:
            handler.terminator = ""

    def reset_no_line_break_log(self) -> None:
        for handler, default_terminator in self.default_terminators:
            handler.terminator = default_terminator
        del self.default_terminators

    def show_stream(
        self, response: Generator[dict[str, Any], None, None], max_size: int
    ) -> dict[str, str]:
        message = {"role": "", "content": ""}
        for chunk in response:
            delta = chunk["choices"][0]["delta"]
            if "role" in delta:
                self.log.info(
                    self.get_output(
                        {"role": delta["role"], "content": ""},
                        max_size,
                    )
                )
                message["role"] = delta["role"]
            if "content" in delta:
                self.log.info(delta["content"])
                message["content"] += delta["content"]
            finish_reason = chunk["choices"][0]["finish_reason"]
            if finish_reason == "length":
                self.log.warning("Too much tokens.\n")
            elif finish_reason == "content_filter":
                self.log.warning(
                    "Omitted content due to a flag from the content filters.\n"
                )
        self.log.info("\n")
        return message

    def chat(self, messages: Messages) -> float:
        max_tokens_orig = self.max_tokens
        if self.max_tokens == 0:
            # Set minimum max_tokens for chat
            self.max_tokens = 100

        messages = self.fix_messages(messages)
        tokens = [
            num_tokens_from_message(message, self.model)
            for message in messages
        ]
        prompt_tokens = num_total_tokens(sum(tokens), self.model)
        self.check_prompt_tokens(prompt_tokens)

        max_size = max(
            10, max(len(self.get_name(message)) for message in messages)
        )
        for message in messages:
            self.log.info(self.get_output(message, max_size))

        self.set_no_line_break_log()
        cost = 0.0
        try:
            while True:
                self.log.info(
                    self.get_output({"role": "user", "content": ""}, max_size)
                )
                message = {"role": "user", "content": input()}
                if message["content"].lower() in self.chat_exit_cmd:
                    break
                message_tokens = num_tokens_from_message(message, self.model)
                if (
                    num_total_tokens(message_tokens, self.model)
                    >= model_max_tokens[self.model] - self.max_tokens
                ):
                    self.log.warning("Input is too long, try shorter.\n")
                    continue
                messages.append(message)
                tokens.append(message_tokens)
                while (
                    prompt_tokens := num_total_tokens(sum(tokens), self.model)
                ) >= model_max_tokens[self.model] - self.max_tokens:
                    messages = messages[1:]
                    tokens = tokens[1:]
                cost += prices[self.model][0] * prompt_tokens / 1000.0
                response = cast(
                    Generator[dict[str, Any], None, None],
                    self.completion(messages, stream=True),
                )
                new_message = self.show_stream(response, max_size)
                messages.append(new_message)
                cost += (
                    prices[self.model][1]
                    * num_tokens_from_message(
                        new_message, self.model, only_content=True
                    )
                    / 1000.0
                )
        except KeyboardInterrupt:
            pass

        message = {"role": "assistant", "content": "Bye!"}
        self.log.info(self.get_output(message, max_size))
        self.log.info("\n")

        self.reset_no_line_break_log()
        self.max_tokens = max_tokens_orig
        return cost
