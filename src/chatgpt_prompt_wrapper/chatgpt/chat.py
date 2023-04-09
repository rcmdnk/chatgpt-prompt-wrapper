import logging
from dataclasses import dataclass, field
from typing import Any, Generator, cast

from .chatgpt import ChatGPT, Messages


@dataclass
class Chat(ChatGPT):
    """Chat class for interacting with OpenAI's API.

    Parameters
    ----------
    chat_exit_cmd: list[str]
        The command to exit the chat.
    """

    chat_exit_cmd: list[str] = field(
        default_factory=lambda: ["exit", "quit", "bye", "bye!"]
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

    def run(self, messages: Messages) -> float:
        max_tokens_orig = self.max_tokens
        if self.max_tokens == 0:
            # Set minimum max_tokens for chat
            self.max_tokens = 100

        messages = self.fix_messages(messages)
        tokens = [
            self.num_tokens_from_message(message) for message in messages
        ]
        prompt_tokens = self.num_total_tokens(sum(tokens))
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
                message_tokens = self.num_tokens_from_message(message)
                if (
                    self.num_total_tokens(message_tokens)
                    >= self.model_max_tokens[self.model] - self.max_tokens
                ):
                    self.log.warning("Input is too long, try shorter.\n")
                    continue
                messages.append(message)
                tokens.append(message_tokens)
                while (
                    prompt_tokens := self.num_total_tokens(sum(tokens))
                ) >= self.model_max_tokens[self.model] - self.max_tokens:
                    messages = messages[1:]
                    tokens = tokens[1:]
                cost += self.prices[self.model][0] * prompt_tokens / 1000.0
                response = cast(
                    Generator[dict[str, Any], None, None],
                    self.completion(messages, stream=True),
                )
                new_message = self.show_stream(response, max_size)
                messages.append(new_message)
                cost += (
                    self.prices[self.model][1]
                    * self.num_tokens_from_message(
                        new_message, only_content=True
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
