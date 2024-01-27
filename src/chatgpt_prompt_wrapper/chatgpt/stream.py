import logging
from dataclasses import dataclass
from typing import Any, Generator

from inherit_docstring import inherit_docstring

from .chatgpt import ChatGPT, Messages


@inherit_docstring
@dataclass
class Stream(ChatGPT):
    """Stream chat class with ChatGPT."""

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
        name: str = "",
    ) -> dict[str, str]:
        message = {"role": "", "content": ""}
        if name:
            message["name"] = name
        for chunk in response:
            delta = chunk["choices"][0]["delta"]
            if "role" in delta:
                message["role"] = delta["role"]
                self.log.info(self.get_output(message, max_size))
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

        # Remove the name from the message, as it fails if it does not match '^[a-zA-Z0-9_-]{1,64}$'.
        if "name" in message:
            del message["name"]
        self.log.info("\n")
        return message

    def run_main(self, messages: Messages) -> tuple[int, float]:
        return (0, 0)

    def run(self, messages: Messages) -> float:
        self.finish_chat = False
        self.set_no_line_break_log()

        max_size, cost = self.run_main(messages)

        self.reset_no_line_break_log()
        message = {"role": "assistant", "content": "Bye!"}
        self.log.info(self.get_output(message, max_size))
        return cost
