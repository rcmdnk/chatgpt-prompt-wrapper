import logging
from dataclasses import dataclass, field
from typing import Any, Generator, cast

from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.named_commands import accept_line
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.styles import Style

from .chatgpt import ChatGPT, Messages


@dataclass
class Chat(ChatGPT):
    """Chat class for interacting with OpenAI's API.

    Parameters
    ----------
    multiline : bool
        Whether to use multiline prompt.
    vi: bool
        If true, use the vi keybindings at input prompt (default is emacs key bindings).
    chat_exit_cmd: list[str]
        The command to exit the chat.
    """

    multiline: bool = True
    vi: bool = False
    chat_exit_cmd: list[str] = field(
        default_factory=lambda: ["bye", "bye!", "exit", "quit"]
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        self.make_prompt()

    def make_prompt(self) -> None:
        if self.multiline:
            toolbar_text = f"Send text: <b>[Meta+Enter]</b>, <b>[Esc]</b><b>[Enter]</b>. Exit chat: <b>[Ctrl-C]</b>, <b>{self.chat_exit_cmd[0]}</b>, "
        else:
            toolbar_text = (
                f"Exit chat: <b>[Ctrl-C]</b>, <b>{self.chat_exit_cmd[0]}</b>,"
            )
        if self.vi:
            toolbar_text += "<b>Vi mode</b>."
        else:
            toolbar_text += "<b>emacs mode</b>."
        toolbar_view = HTML(toolbar_text)

        def bottom_toolbar() -> HTML:
            return toolbar_view

        def prompt_continuation(
            width: int, line_number: int, is_soft_wrap: bool
        ) -> str:
            return ""

        style_dict = {"": ""}  # Text (normal color)
        for k, v in self.colors.items():
            if v in self.ansi_colors:
                style_dict[k] = f"ansi{v} bold"
        style = Style.from_dict(style_dict)

        bindings = KeyBindings()

        @bindings.add("c-c")
        def _(event: KeyPressEvent) -> None:
            self.finish_chat = True
            accept_line(event)

        self.prompt_params = {
            "style": style,
            "multiline": self.multiline,
            "prompt_continuation": prompt_continuation,
            "bottom_toolbar": bottom_toolbar,
            "key_bindings": bindings,
            "vi_mode": self.vi,
        }

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
        messages = self.fix_messages(messages)
        tokens = [
            self.num_tokens_from_message(message) for message in messages
        ]
        prompt_tokens = self.num_total_tokens(sum(tokens))
        self.check_prompt_tokens(prompt_tokens)

        max_size = (
            max(10, max(len(self.get_name(message)) for message in messages))
            if messages
            else 10
        )
        for message in messages:
            self.log.info(self.get_output(message, max_size))

        self.set_no_line_break_log()
        cost = 0.0
        self.finish_chat = False
        while True:
            user = [("class:user", f"{self.alias['user']:>{max_size}}> ")]
            text = prompt(user, **self.prompt_params)  # type: ignore
            if self.finish_chat:
                break
            message = {"role": "user", "content": text}
            if message["content"].lower() in self.chat_exit_cmd:
                break
            message_tokens = self.num_tokens_from_message(message)
            if (
                self.num_total_tokens(message_tokens)
                > self.tokens_limit - self.min_max_tokens
            ):
                self.log.warning("Input is too long, try shorter.\n")
                continue
            messages.append(message)
            tokens.append(message_tokens)
            while (
                prompt_tokens := self.num_total_tokens(sum(tokens))
            ) > self.tokens_limit - self.min_max_tokens:
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
                * self.num_tokens_from_message(new_message, only_content=True)
                / 1000.0
            )

        message = {"role": "assistant", "content": "Bye!"}
        self.log.info(self.get_output(message, max_size))
        self.log.info("\n")

        self.reset_no_line_break_log()
        return cost
