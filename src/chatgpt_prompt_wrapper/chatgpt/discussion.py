import logging
from dataclasses import dataclass, field
from typing import Any, Generator, cast

from .chatgpt import ChatGPT, Messages


@dataclass
class Discussion(ChatGPT):
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
        self,
        response: Generator[dict[str, Any], None, None],
        max_size: int,
        role: str,
    ) -> dict[str, str]:
        message = {"role": "assistant", "content": ""}
        self.log.info(
            self.get_output(
                {"role": role, "name": self.names[role], "content": ""},
                max_size,
            )
        )
        for chunk in response:
            delta = chunk["choices"][0]["delta"]
            if "content" in delta:
                self.log.info(delta["content"])
                message["content"] += delta["content"]
            finish_reason = chunk["choices"][0]["finish_reason"]
            if finish_reason == "length":
                self.log.warning(
                    "The reply was truncated due to the tokens limit.\n"
                )
            elif finish_reason == "content_filter":
                self.log.warning(
                    "The reply was omitted due to the content filters.\n"
                )
        self.log.info("\n")
        return message

    def run(self, messages: Messages) -> float:
        if len(messages) < 3:
            raise ValueError("The discussion must have at least 3 messages.")
        system_message = messages[0]
        if system_message["role"] != "theme":
            raise ValueError(
                "The first message for the discussion must be a theme."
            )
        system_message["role"] = "system"
        gpt1 = messages[1]
        if gpt1["role"] != "gpt1":
            raise ValueError(
                "The second message for the discussion must be a gpt1's role."
            )
        gpt1["role"] = "system"
        gpt2 = messages[2]
        if gpt2["role"] != "gpt2":
            raise ValueError(
                "The third message for the discussion must be a gpt2's role."
            )
        gpt2["role"] = "system"

        gpt1_messages = [system_message, gpt1]
        gpt2_messages = [system_message, gpt2]

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

        max_size = max(10, *[len(x) for x in self.names])
        self.log.info(f"Theme: {messages[0]['content']}")

        cost = 0.0
        self.finish_chat = False
        self.set_no_line_break_log()
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
                new_message = self.show_stream(response, max_size, "gpt1")
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
                new_message = self.show_stream(response, max_size, "gpt2")
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
            pass
        self.reset_no_line_break_log()
        message = {"role": "assistant", "content": "Bye!"}
        self.log.info(self.get_output(message, max_size))
        return cost
