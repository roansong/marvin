from marvin.pydantic import Field, SecretStr
from marvin.utilities.module_loading import import_string
from marvin.core.ChatCompletion.base import (
    BaseChatCompletion,
    BaseChatCompletionSettings,
    BaseChatRequest,
    BaseChatResponse,
)


class ChatCompletionSettings(BaseChatCompletionSettings):
    """
    Provider-specific settings.
    """

    model: str = "gpt-3.5-turbo"
    api_key: SecretStr = Field(None, env=["MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"])
    organization: str = Field(None)
    api_type: str = None
    api_base: str = Field(None, description="The endpoint the OpenAI API.")
    api_version: str = Field(None, description="The API version")

    class Config(BaseChatCompletionSettings.Config):
        env_prefix = "MARVIN_OPENAI_"
        exclude_none = True


class ChatRequest(BaseChatRequest):
    _config = ChatCompletionSettings()


class ChatResponse(BaseChatResponse):
    @property
    def message(self):
        """
        This property extracts the message from the raw response.
        If there is only one choice, it returns the message from that choice.
        Otherwise, it returns a list of messages from all choices.
        """
        if len(self.raw.choices) == 1:
            return next(iter(self.raw.choices)).message
        return [x.message for x in self.raw.choices]

    @property
    def function_call(self):
        """
        This property extracts the function call from the message.
        If the message is a list, it returns a list of function calls from all messages.
        Otherwise, it returns the function call from the message.
        """
        if isinstance(self.message, list):
            return [x.function_call for x in self.message]
        return self.message.function_call


class ChatCompletion(BaseChatCompletion):
    _module: str = "openai.ChatCompletion"
    _request_class: str = f"{__name__}.ChatRequest"
    _response_class: str = f"{__name__}.ChatResponse"
    _create: str = "create"
    _acreate: str = "acreate"

    def prepare_request(self, **kwargs):
        """
        Nothing to change since BaseChatCompletion is designed
        off of the OpenAI API.
        """
        return super().prepare_request(**kwargs)