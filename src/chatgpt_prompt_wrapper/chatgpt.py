import logging
from dataclasses import dataclass

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


# Ref: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
def num_tokens_from_messages(
    messages: Messages, model: str = "gpt-3.5-turbo"
) -> int:
    encoding = tiktoken.encoding_for_model(model)
    if "gpt-3.5" in model:
        tokens_per_message = (
            4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        )
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-4" in model:
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise ChatGPTPromptWrapperError(f"Model: {model} is not supported.")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


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
        The maximum number of tokens to generate in the chat completion. Set 0 to use the max values for the model minus prompt tokens.
    temperature: float
        Sampling temperature (0 ~ 2).
    top_p: float
        Probability (0 ~ 1) that the model will consider the top_p tokens. Do not set both temperature and top_p in the same time.
    presence_penalty: float
        The penalty for the model to return the same token (-2 ~ 2).
    frequency_penalty: float
        The penalty for the model to return the same token multiple times (-2 ~ 2).
    """

    key: str
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 0
    temperature: float = 1
    top_p: float = 1
    presence_penalty: float = 0
    frequency_penalty: float = 0

    def __post_init__(self) -> None:
        self.log = logging.getLogger(__name__)
        openai.api_key = self.key

    def get_max_tokens(self, messages: Messages) -> int:
        prompt_tokens = num_tokens_from_messages(messages, self.model)
        if prompt_tokens >= model_max_tokens[self.model]:
            raise ChatGPTPromptWrapperError(
                f"Too much tokens: prompt tokens ({prompt_tokens}) >= model's max tokens ({model_max_tokens[self.model]})."
            )

        if self.max_tokens == 0:
            # it must be maximum tokens for model - 1
            max_tokens = model_max_tokens[self.model] - prompt_tokens - 1
        else:
            max_tokens = self.max_tokens
            if max_tokens + prompt_tokens >= model_max_tokens[self.model]:
                self.log.warning(
                    f"Too much tokens: prompt tokens ({prompt_tokens}) + completion tokens (max_tokens) ({max_tokens}) >= model's max tokens ({model_max_tokens[self.model]})."
                )
                max_tokens = model_max_tokens[self.model] - prompt_tokens - 1
                self.log.warning(f"Set max_tokens to {max_tokens}.")
        return max_tokens

    def fix_messages(self, messages: Messages) -> Messages:
        if "gpt-3.5" in self.model:
            for message in messages:
                if message["role"] == "system":
                    message["role"] = "user"
        return messages

    def chat(self, messages: Messages) -> str:
        """Chat with the model.

        Parameters
        ----------
        messages : list[dict[str, str]]
            The messages to use.
        """
        messages = self.fix_messages(messages)
        max_tokens = self.get_max_tokens(messages)

        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
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
                "Omitted content due to a flag from our content filters."
            )
        elif finish_reason is None:
            self.log.warning("API response still in progress or incomplete")
        else:
            raise ChatGPTPromptWrapperError(
                f"Unknown finish_reason: {response['choices'][0]['finish_reason']}"
            )
        return response["choices"][0]["message"]["content"]
