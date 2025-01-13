from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from inherit_docstring import inherit_docstring

from ..chatgpt_prompt_wrapper_exception import ChatGPTPromptWrapperError
from .chatgpt import ChatGPT, Messages

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion


@inherit_docstring
@dataclass
class Ask(ChatGPT):
    """Ask class for OpenAI's API.

    Parameters
    ----------
    show: bool
        Whether to show the prompt.

    """

    show: bool = False

    def get_tokens(self, response: ChatCompletion) -> tuple[int, int]:
        if response.usage:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
        else:
            self.log.warning("API response does not have usage information")
            prompt_tokens = 0
            completion_tokens = 0
        return prompt_tokens, completion_tokens

    def run(self, messages: Messages) -> float:
        messages = self.fix_messages(messages)
        max_size = max(
            10,
            max(len(self.get_name(message)) for message in messages),
        )
        if self.show:
            for message in messages:
                self.log.info(self.get_output(message, max_size))
        response = self.completion_message(messages)
        prompt_tokens, completion_tokens = self.get_tokens(response)

        finish_reason = response.choices[0].finish_reason
        if finish_reason == "stop":
            pass
        elif finish_reason == "length":
            if self.max_output_tokens:
                reason = f"max_output_tokens for completion = {self.max_output_tokens}."
            else:
                reason = f"max_output_tokens for completion = {self.get_max_completion_tokens(messages)} (prompt tokens: {prompt_tokens}, context_window: {self.context_window}, minimum of output tokens: {self.min_output_tokens})."
            self.log.warning(
                f"The reply was truncated due to the tokens limit: {reason}",
            )
        elif finish_reason == "content_filter":
            self.log.warning(
                "The reply was omitted due to the content filters.",
            )
        elif finish_reason is None:
            self.log.warning("API response is incomplete")
        else:
            raise ChatGPTPromptWrapperError(
                f"Unknown finish_reason: {response.choices[0].finish_reason}",
            )
        if self.show:
            answer = self.get_output(
                response.choices[0].message.to_dict(),
                max_size,
            )
        elif response.choices[0].message.content:
            answer = response.choices[0].message.content
        else:
            answer = ""
        self.log.info(answer)

        return (
            self.prices[self.model][0] * prompt_tokens / 1000.0
            + self.prices[self.model][1] * completion_tokens / 1000.0
        )
