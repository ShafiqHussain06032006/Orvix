from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Request
from langchain.prompts.prompt import PromptTemplate
from sse_starlette import EventSourceResponse

from chatchat.server.api_server.api_schemas import OpenAIChatInput
from chatchat.server.chat.chat import chat
from chatchat.server.chat.kb_chat import kb_chat
from chatchat.server.chat.feedback import chat_feedback
from chatchat.server.chat.file_chat import file_chat
from chatchat.server.db.repository import add_message_to_db
from chatchat.server.utils import (
    get_OpenAIClient,
    get_prompt_template,
    get_tool,
    get_tool_config,
)
from chatchat.settings import Settings
from chatchat.utils import build_logger
from .openai_routes import openai_request, OpenAIChatOutput


logger = build_logger()

chat_router = APIRouter(prefix="/chat", tags=["ChatChat conversation"])

# chat_router.post(
#     "/chat",
#     summary="Talk to llm models (via LLMChain)",
# )(chat)

chat_router.post(
    "/feedback",
    summary="Returns llm model dialogue score",
)(chat_feedback)


chat_router.post("/kb_chat", summary="Knowledge Base Chat")(kb_chat)
chat_router.post("/file_chat", summary="file conversation")(file_chat)


@chat_router.post("/chat/completions", summary="Unified chat interface compatible with openai")
async def chat_completions(
    request: Request,
    body: OpenAIChatInput,
) -> Dict:
    """
    The request parameters are consistent with openai.chat.completions.create, and additional parameters can be passed in through extra_body
    Tools and tool_choice can directly pass the tool name, which will be converted according to the tools included in the project.
    Different chat functions are called with different parameter combinations:
    - tool_choice
        - extra_body contains tool_input: directly call tool_choice(tool_input)
        - extra_body does not contain tool_input: call tool_choice through agent
    - tools: agent dialogue
    - Others: LLM dialogue
    Other combinations (such as file conversations) will also be considered in the future.
    Returns a Dict compatible with openai
    """
    # import rich
    # rich.print(body)

    # When this interface is called and no body is passed in "max_tokens" parameter, the value defined in the configuration is used by default.
    if body.max_tokens in [None, 0]:
        body.max_tokens = Settings.model_settings.MAX_TOKENS

    client = get_OpenAIClient(model_name=body.model, is_async=True)
    extra = {**body.model_extra} or {}
    for key in list(extra):
        delattr(body, key)

    # check tools & tool_choice in request body
    if isinstance(body.tool_choice, str):
        if t := get_tool(body.tool_choice):
            body.tool_choice = {"function": {"name": t.name}, "type": "function"}
    if isinstance(body.tools, list):
        for i in range(len(body.tools)):
            if isinstance(body.tools[i], str):
                if t := get_tool(body.tools[i]):
                    body.tools[i] = {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.args,
                        },
                    }

    conversation_id = extra.get("conversation_id")
  
    try:
        message_id = (
            add_message_to_db(
                chat_type="agent_chat",
                query=body.messages[-1]["content"],
                conversation_id=conversation_id,
            )
            if conversation_id
            else None
        )
    except Exception as e:
        logger.warning(f"failed to add message to db: {e}")
        message_id = None

    chat_model_config = {}  # TODO: Front-end supports configuration model
    tool_config = {}
    if body.tools:
        tool_names = [x["function"]["name"] for x in body.tools]
        tool_config = {name: get_tool_config(name) for name in tool_names}

    result = await chat(
        query=body.messages[-1]["content"],
        metadata=extra.get("metadata", {}),
        conversation_id=extra.get("conversation_id", ""),
        message_id=message_id,
        history_len=-1,
        stream=body.stream,
        chat_model_config=extra.get("chat_model_config", chat_model_config),
        tool_config=tool_config,
        use_mcp=extra.get("use_mcp", False),
        max_tokens=body.max_tokens,
    )
    return result
