import logging
from dataclasses import dataclass, field
from typing import Any, Generator, cast

from inherit_docstring import inherit_docstring

from ..chatgpt_prompt_wrapper_exception import ChatGPTPromptWrapperError
from .chatgpt import Messages
from .stream import Stream


@inherit_docstring
@dataclass
class Discuss(Stream):
    """Discussion between ChatGPTs.

    Parameters
    ----------
    colors: dict[str, str]
        The colors to use for the different roles.
    names: dict[str, str]
        The names to use for the different roles.
    """

    colors: dict[str, str] = field(
        default_factory=lambda: {
            "gpt1": "blue",
            "gpt2": "purple",
        }
    )
    names: dict[str, str] = field(
        default_factory=lambda: {
            "gpt1": "gpt1",
            "gpt2": "gpt2",
        }
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        for k, v in self.names.items():
            if v not in self.colors and k in self.colors:
                self.colors[v] = self.colors[k]

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

    def prepare_messages(
        self, messages: Messages
    ) -> tuple[Messages, Messages, list[int], list[int]]:
        theme = {}
        gpt1 = {
            "role": "system",
            "content": "Please engage in the discussion as a supporter.",
        }
        gpt2 = {
            "role": "system",
            "content": "Please engage in the discussion as a opponent.",
        }
        for message in messages:
            if message["role"] == "theme":
                theme = message
                theme["role"] = "system"
            elif message["role"] == "gpt1":
                gpt1 = message
                gpt1["role"] = "system"
            elif message["role"] == "gpt2":
                gpt2 = message
                gpt2["role"] = "system"
            elif message["role"] in ["user", "system"]:
                if theme:
                    theme["content"] += "\n" + message["content"]
                else:
                    theme = message
                    theme["role"] = "system"
        if not theme or not gpt1 or not gpt2:
            self.reset_no_line_break_log()
            raise ChatGPTPromptWrapperError(
                "The discuss mode must have a theme (or given by a message from the command line), gpt1, and gpt2 roles."
            )
        gpt1_messages = [theme, gpt1]
        gpt2_messages = [theme, gpt2]

        tokens1 = [
            self.num_tokens_from_message(message) for message in gpt1_messages
        ]
        tokens2 = [
            self.num_tokens_from_message(message) for message in gpt2_messages
        ]

        prompt_tokens1 = self.num_total_tokens(sum(tokens1))
        self.check_prompt_tokens(prompt_tokens1)
        prompt_tokens2 = self.num_total_tokens(sum(tokens2))
        self.check_prompt_tokens(prompt_tokens2)

        return gpt1_messages, gpt2_messages, tokens1, tokens2

    def run_main(self, messages: Messages) -> tuple[int, float]:
        gpt1_messages, gpt2_messages, tokens1, tokens2 = self.prepare_messages(
            messages
        )
        max_size = max(10, *[len(x) for x in self.names])
        self.log.info(f"Theme: {messages[0]['content']}\n")

        cost = 0.0
        try:
            while True:
                _ = input()

                while (
                    prompt_tokens := self.num_total_tokens(sum(tokens1))
                ) > self.tokens_limit - self.min_max_tokens:
                    gpt1_messages = gpt1_messages[:2] + gpt1_messages[3:]
                    tokens1 = tokens1[:2] + tokens1[3:]
                cost += self.prices[self.model][0] * prompt_tokens / 1000.0
                response = cast(
                    Generator[dict[str, Any], None, None],
                    self.completion(gpt1_messages, stream=True),
                )

                new_message = self.show_stream(
                    response, max_size, name=self.names.get("gpt1", "gpt1")
                )
                gpt1_messages.append(new_message)
                tokens = self.num_tokens_from_message(new_message)
                tokens1.append(tokens)
                user_message = {
                    "role": "user",
                    "content": new_message["content"],
                }
                gpt2_messages.append(user_message)
                tokens = self.num_tokens_from_message(user_message)
                tokens2.append(tokens)

                cost += (
                    self.prices[self.model][1]
                    * self.num_tokens_from_message(
                        new_message, only_content=True
                    )
                    / 1000.0
                )

                _ = input()
                while (
                    prompt_tokens := self.num_total_tokens(sum(tokens2))
                ) > self.tokens_limit - self.min_max_tokens:
                    gpt2_messages = gpt2_messages[:2] + gpt2_messages[3:]
                    tokens2 = tokens2[:2] + tokens2[3:]
                cost += self.prices[self.model][0] * prompt_tokens / 1000.0
                response = cast(
                    Generator[dict[str, Any], None, None],
                    self.completion(gpt2_messages, stream=True),
                )
                new_message = self.show_stream(
                    response, max_size, name=self.names.get("gpt2", "gpt2")
                )
                gpt2_messages.append(new_message)
                tokens = self.num_tokens_from_message(new_message)
                tokens2.append(tokens)
                user_message = {
                    "role": "user",
                    "content": new_message["content"],
                }
                gpt1_messages.append(user_message)
                tokens = self.num_tokens_from_message(user_message)
                tokens1.append(tokens)

                cost += (
                    self.prices[self.model][1]
                    * self.num_tokens_from_message(
                        new_message, only_content=True
                    )
                    / 1000.0
                )
        except KeyboardInterrupt:
            self.log.info("\n")
        return max_size, cost
