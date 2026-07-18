from __future__ import annotations

from typing import List, Literal

from fastapi import APIRouter, Request

from chatchat.settings import Settings
from chatchat.server.api_server.api_schemas import OpenAIChatInput, OpenAIChatOutput
from chatchat.server.chat.file_chat import upload_temp_docs
from chatchat.server.chat.kb_chat import kb_chat
from chatchat.server.knowledge_base.kb_api import create_kb, delete_kb, list_kbs
from chatchat.server.knowledge_base.kb_doc_api import (
    delete_docs,
    download_doc,
    list_files,
    recreate_vector_store,
    search_docs,
    update_docs,
    update_info,
    upload_docs,
    search_temp_docs,
)
from chatchat.server.knowledge_base.kb_summary_api import (
    recreate_summary_vector_store,
    summary_doc_ids_to_vector_store,
    summary_file_to_vector_store,
)
from chatchat.server.utils import BaseResponse, ListResponse
from chatchat.server.knowledge_base.kb_cache.faiss_cache import memo_faiss_pool


kb_router = APIRouter(prefix="/knowledge_base", tags=["Knowledge Base Management"])


@kb_router.post(
    "/{mode}/{param}/chat/completions", summary="knowledge base dialogue, openai compatible, parameters consistent with /chat/kb_chat"
)
async def kb_chat_endpoint(
    mode: Literal["local_kb", "temp_kb", "search_engine"],
    param: str,
    body: OpenAIChatInput,
    request: Request,
):
    # import rich
    # rich.print(body)

    if body.max_tokens in [None, 0]:
        body.max_tokens = Settings.model_settings.MAX_TOKENS

    extra = body.model_extra
    ret = await kb_chat(
        query=body.messages[-1]["content"],
        mode=mode,
        kb_name=param,
        top_k=extra.get("top_k", Settings.kb_settings.VECTOR_SEARCH_TOP_K),
        score_threshold=extra.get("score_threshold", Settings.kb_settings.SCORE_THRESHOLD),
        history=body.messages[:-1],
        stream=body.stream,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        prompt_name=extra.get("prompt_name", "default"),
        return_direct=extra.get("return_direct", False),
        request=request,
    )
    return ret


kb_router.get(
    "/list_knowledge_bases", response_model=ListResponse, summary="List knowledge bases"
)(list_kbs)

kb_router.post(
    "/create_knowledge_base", response_model=BaseResponse, summary="Create knowledge base"
)(create_kb)

kb_router.post(
    "/delete_knowledge_base", response_model=BaseResponse, summary="Delete knowledge base"
)(delete_kb)

kb_router.get(
    "/list_files", response_model=ListResponse, summary="Get a list of files in the knowledge base"
)(list_files)

kb_router.post("/search_docs", response_model=List[dict], summary="Search knowledge base")(
    search_docs
)

kb_router.post(
    "/upload_docs",
    response_model=BaseResponse,
    summary="Upload files to the knowledge base and/or vectorize them",
)(upload_docs)

kb_router.post(
    "/delete_docs", response_model=BaseResponse, summary="Delete the specified file in the knowledge base"
)(delete_docs)

kb_router.post("/update_info", response_model=BaseResponse, summary="Update knowledge base introduction")(
    update_info
)

kb_router.post(
    "/update_docs", response_model=BaseResponse, summary="Update existing files to the knowledge base"
)(update_docs)

kb_router.get("/download_doc", summary="Download the corresponding knowledge file")(download_doc)

kb_router.post(
    "/recreate_vector_store", summary="Reconstruct the vector library based on the documents in the content and stream the processing progress."
)(recreate_vector_store)

kb_router.post("/upload_temp_docs", summary="Upload files to a temporary directory for file conversations.")(
    upload_temp_docs
)

kb_router.post("/search_temp_docs", summary="Search temporary knowledge base")(
    search_temp_docs
)

# @kb_router.post("/list_temp_kbs", summary="List all temporary knowledge bases")
# def list_temp_kbs():
#     return list(memo_faiss_pool.keys())


summary_router = APIRouter(prefix="/kb_summary_api")
summary_router.post(
    "/summary_file_to_vector_store", summary="Single knowledge base summary based on file name"
)(summary_file_to_vector_store)
summary_router.post(
    "/summary_doc_ids_to_vector_store",
    summary="Individual knowledge base summary based on doc_ids",
    response_model=BaseResponse,
)(summary_doc_ids_to_vector_store)
summary_router.post("/recreate_summary_vector_store", summary="Reconstruct a single knowledge base file summary")(
    recreate_summary_vector_store
)

kb_router.include_router(summary_router)
