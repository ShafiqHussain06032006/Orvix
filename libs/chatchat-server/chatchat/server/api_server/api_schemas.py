from __future__ import annotations

import json
import time
from typing import Dict, List, Literal, Optional, Union

from fastapi import UploadFile
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolChoiceOptionParam,
    ChatCompletionToolParam,
    completion_create_params,
)

from chatchat.settings import Settings
from langchain_chatchat.callbacks.agent_callback_handler import AgentStatus  # noaq
from chatchat.server.pydantic_v2 import AnyUrl, BaseModel, Field
from chatchat.server.utils import MsgType, get_default_llm


class OpenAIBaseInput(BaseModel):
    user: Optional[str] = None
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict] = None
    extra_query: Optional[Dict] = None
    extra_json: Optional[Dict] = Field(None, alias="extra_body")
    timeout: Optional[float] = None

    class Config:
        extra = "allow"


class OpenAIChatInput(OpenAIBaseInput):
    messages: List[ChatCompletionMessageParam]
    model: str = get_default_llm()
    frequency_penalty: Optional[float] = None
    function_call: Optional[completion_create_params.FunctionCall] = None
    functions: List[completion_create_params.Function] = None
    logit_bias: Optional[Dict[str, int]] = None
    logprobs: Optional[bool] = None
    max_tokens: Optional[int] = None
    n: Optional[int] = None
    presence_penalty: Optional[float] = None
    response_format: completion_create_params.ResponseFormat = None
    seed: Optional[int] = None
    stop: Union[Optional[str], List[str]] = None
    stream: Optional[bool] = None
    temperature: Optional[float] = Settings.model_settings.TEMPERATURE
    tool_choice: Optional[Union[ChatCompletionToolChoiceOptionParam, str]] = None
    tools: List[Union[ChatCompletionToolParam, str]] = None
    top_logprobs: Optional[int] = None
    top_p: Optional[float] = None


class OpenAIEmbeddingsInput(OpenAIBaseInput):
    input: Union[str, List[str]]
    model: str
    dimensions: Optional[int] = None
    encoding_format: Optional[Literal["float", "base64"]] = None


class OpenAIImageBaseInput(OpenAIBaseInput):
    model: str
    n: int = 1
    response_format: Optional[Literal["url", "b64_json"]] = None
    size: Optional[
        Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"]
    ] = "256x256"


class OpenAIImageGenerationsInput(OpenAIImageBaseInput):
    prompt: str
    quality: Literal["standard", "hd"] = None
    style: Optional[Literal["vivid", "natural"]] = None


class OpenAIImageVariationsInput(OpenAIImageBaseInput):
    image: Union[UploadFile, AnyUrl]


class OpenAIImageEditsInput(OpenAIImageVariationsInput):
    prompt: str
    mask: Union[UploadFile, AnyUrl]


class OpenAIAudioTranslationsInput(OpenAIBaseInput):
    file: Union[UploadFile, AnyUrl]
    model: str
    prompt: Optional[str] = None
    response_format: Optional[str] = None
    temperature: float = Settings.model_settings.TEMPERATURE


class OpenAIAudioTranscriptionsInput(OpenAIAudioTranslationsInput):
    language: Optional[str] = None
    timestamp_granularities: Optional[List[Literal["word", "segment"]]] = None


class OpenAIAudioSpeechInput(OpenAIBaseInput):
    input: str
    model: str
    voice: str
    response_format: Optional[
        Literal["mp3", "opus", "aac", "flac", "pcm", "wav"]
    ] = None
    speed: Optional[float] = None


# class OpenAIFileInput(OpenAIBaseInput):
#     file: UploadFile # FileTypes
#     purpose: Literal["fine-tune", "assistants"] = "assistants"


class OpenAIBaseOutput(BaseModel):
    id: Optional[str] = None
    content: Optional[str] = None
    model: Optional[str] = None
    object: Literal[
        "chat.completion", "chat.completion.chunk"
    ] = "chat.completion.chunk"
    role: Literal["assistant"] = "assistant"
    finish_reason: Optional[str] = None
    created: int = Field(default_factory=lambda: int(time.time()))
    tool_calls: List[Dict] = []

    status: Optional[int] = None  # AgentStatus
    message_type: int = MsgType.TEXT
    message_id: Optional[str] = None  # id in database table
    is_ref: bool = False  # wheather show in seperated expander

    class Config:
        extra = "allow"

    def model_dump(self) -> dict:
        result = {
            "id": self.id,
            "object": self.object,
            "model": self.model,
            "created": self.created,
            "status": self.status,
            "message_type": self.message_type,
            "message_id": self.message_id,
            "is_ref": self.is_ref,
            **(self.model_extra or {}),
        }

        if self.object == "chat.completion.chunk":
            result["choices"] = [
                {
                    "delta": {
                        "content": self.content,
                        "tool_calls": self.tool_calls,
                    },
                    "role": self.role,
                }
            ]
        elif self.object == "chat.completion":
            result["choices"] = [
                {
                    "message": {
                        "role": self.role,
                        "content": self.content,
                        "finish_reason": self.finish_reason,
                        "tool_calls": self.tool_calls,
                    }
                }
            ]
        return result

    def model_dump_json(self):
        return json.dumps(self.model_dump(), ensure_ascii=False)


class OpenAIChatOutput(OpenAIBaseOutput):
    ...


# MCP Connection related Schema
class MCPConnectionCreate(BaseModel):
    """Create request body for MCP connection"""
    server_name: str = Field(..., min_length=1, max_length=100, description="Server name")
    args: List[str] = Field(default=[], description="Command parameters")
    env: Dict[str, str] = Field(default={}, description="environment variables")
    cwd: Optional[str] = Field(None, description="working directory")
    transport: str = Field(default="stdio", pattern="^(stdio|sse)$", description="Transmission method")
    timeout: int = Field(default=30, ge=1, le=300, description="Connection timeout (seconds)")
    enabled: bool = Field(default=True, description="Whether to enable")
    description: Optional[str] = Field(None, max_length=1000, description="Connection description")
    config: Dict = Field(default={}, description="Connection configuration")


class MCPConnectionUpdate(BaseModel):
    """Update the request body of the MCP connection"""
    server_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Server name")
    args: Optional[List[str]] = Field(None, description="Command parameters")
    env: Optional[Dict[str, str]] = Field(None, description="environment variables")
    cwd: Optional[str] = Field(None, description="working directory")
    transport: Optional[str] = Field(None, pattern="^(stdio|sse)$", description="Transmission method")
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Connection timeout (seconds)")
    enabled: Optional[bool] = Field(None, description="Whether to enable")
    description: Optional[str] = Field(None, max_length=1000, description="Connection description")
    config: Optional[Dict] = Field(None, description="Connection configuration")


class MCPConnectionResponse(BaseModel):
    """MCP connection response body"""
    id: str
    server_name: str
    args: List[str]
    env: Dict[str, str]
    cwd: Optional[str]
    transport: str
    timeout: int
    enabled: bool
    description: Optional[str]
    config: Dict
    create_time: str
    update_time: Optional[str]

    class Config:
        json_encoders = {
            # Process datetime type
        }


class MCPConnectionListResponse(BaseModel):
    """MCP connection list response body"""
    connections: List[MCPConnectionResponse]
    total: int


class MCPConnectionSearchRequest(BaseModel):
    """MCP connection search request body"""
    keyword: Optional[str] = Field(None, description="Search keywords")
    transport: Optional[str] = Field(None, description="Transport method filtering")
    enabled: Optional[bool] = Field(None, description="Enable status filtering")
    limit: int = Field(default=50, ge=1, le=100, description="Return quantity limit")


class MCPConnectionStatusResponse(BaseModel):
    """MCP connection status response body"""
    success: bool
    message: str
    connection_id: Optional[str] = None


class MCPProfileCreate(BaseModel):
    """MCP common configuration creation request body"""
    timeout: int = Field(default=30, ge=10, le=300, description="Default connection timeout (seconds)")
    working_dir: str = Field(default="/tmp", description="Default working directory")
    env_vars: Dict[str, str] = Field(default={}, description="Default environment variables")


class MCPProfileResponse(BaseModel):
    """MCP common configuration response body"""
    timeout: int
    working_dir: str
    env_vars: Dict[str, str]
    update_time: str


class MCPProfileStatusResponse(BaseModel):
    """MCP common configuration status response body"""
    success: bool
    message: str
