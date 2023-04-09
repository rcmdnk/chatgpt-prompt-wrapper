from dataclasses import dataclass
from typing import Any, cast

from ..chatgpt_prompt_wrapper_exception import ChatGPTPromptWrapperError
from .chatgpt import ChatGPT, Messages


@dataclass
class Ask(ChatGPT):
    """Ask class for OpenAI's API.

    Parameters
    ----------
    show: bool
        Whether to show the prompt.
    """

    show: bool = False

    def run(self, messages: Messages) -> float:
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
                f'Too much tokens: prompt tokens = {response["usage"]["prompt_tokens"]}, completion tokens = {response["usage"]["completion_tokens"]}, while max_tokens = {self.max_tokens}, model\'s max tokens is {self.model_max_tokens[self.model]}.'
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
            self.prices[self.model][0]
            * response["usage"]["prompt_tokens"]
            / 1000.0
            + self.prices[self.model][1]
            * response["usage"]["completion_tokens"]
            / 1000.0
        )
