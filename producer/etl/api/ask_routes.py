"""RAG Q&A endpoint — two-pass: route to source, then answer (query for structured, RAG for unstructured)."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from etl.storage.store import load_pinecone_config, is_pinecone_configured
from etl.output.sheet_store import list_tables, query_sheet

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ask"])


class ChatMessage(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


class Source(BaseModel):
    title: str
    doc_id: str
    url: str
    source_type: str
    chunk_index: int
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    method: str = ""  # "rag" or "sql"
    sql_query: str = ""


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Two-pass Q&A: 1) find relevant source, 2) answer via SQL (structured) or RAG (unstructured)."""
    if not is_pinecone_configured():
        raise HTTPException(status_code=400, detail="Pinecone not configured.")

    pc_config = load_pinecone_config()

    try:
        from openai import OpenAI
        from pinecone import Pinecone

        openai_client = OpenAI(api_key=pc_config["openai_api_key"])
        pc = Pinecone(api_key=pc_config["api_key"])
        index = pc.Index(pc_config["index_name"])

        # === PASS 0: Resolve follow-up into standalone question ===
        resolved_question = request.question
        if request.history:
            history_text = "\n".join(
                f"{m.role}: {m.content}" for m in request.history[-6:]  # Last 3 exchanges
            )
            resolve_completion = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Rewrite the user's follow-up message as a standalone question that includes "
                            "all necessary context from the conversation history. "
                            "Return ONLY the rewritten question, nothing else."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Conversation:\n{history_text}\n\nFollow-up: {request.question}\n\nStandalone question:",
                    },
                ],
                temperature=0,
                max_tokens=200,
            )
            resolved_question = resolve_completion.choices[0].message.content.strip()
            logger.info("Resolved follow-up: '%s' → '%s'", request.question, resolved_question)

        # === PASS 1: Find relevant sources ===
        embed_response = openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=[resolved_question],
        )
        query_vector = embed_response.data[0].embedding

        results = index.query(
            vector=query_vector,
            top_k=5,
            include_metadata=True,
        )

        matches = results.get("matches", [])
        if not matches:
            return AskResponse(answer="No relevant documents found.", sources=[], method="rag")

        # Check if the top match is a structured sheet
        top_match = matches[0]
        top_source_type = top_match.get("metadata", {}).get("source_type", "")

        # === PASS 2A: Structured data — generate and execute SQL ===
        if top_source_type == "structured_sheet":
            return await _answer_structured(
                resolved_question, matches, openai_client, pc_config
            )

        # === PASS 2B: Unstructured data — standard RAG ===
        return _answer_unstructured(resolved_question, matches, openai_client)

    except Exception as e:
        logger.exception("Failed to answer question")
        raise HTTPException(status_code=500, detail=str(e))


async def _answer_structured(
    question: str, matches: list, openai_client, pc_config: dict
) -> AskResponse:
    """Answer using SQL query against SQLite for structured sheet data."""
    # Get schema of available tables
    data_dir = "./data"
    tables = list_tables(data_dir)

    if not tables:
        # Fall back to RAG
        return _answer_unstructured(question, matches, openai_client)

    # Build schema description for the LLM
    schema_desc = "Available tables in SQLite:\n\n"
    for t in tables:
        cols = ", ".join([f"{name} ({dtype})" for name, dtype in t["columns"]])
        schema_desc += f'Table: "{t["table_name"]}" ({t["row_count"]} rows)\n'
        schema_desc += f"  Columns: {cols}\n\n"

    # Also include the Pinecone metadata for context about what the sheets contain
    sheet_context = ""
    for match in matches:
        meta = match.get("metadata", {})
        if meta.get("source_type") == "structured_sheet":
            sheet_context += meta.get("text", "") + "\n"

    # Generate SQL
    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a SQL expert. Generate a SQLite query to answer the user's question. "
                    "Return ONLY the SQL query, no explanation, no markdown, no code blocks. "
                    "Use the exact table and column names from the schema. "
                    "Column names with spaces use underscores. "
                    "For text comparisons, use LIKE with % for partial matches. "
                    "Always use double quotes around table names and column names."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{schema_desc}\n"
                    f"Context about the data:\n{sheet_context}\n\n"
                    f"Question: {question}\n\n"
                    f"SQL query:"
                ),
            },
        ],
        temperature=0,
        max_tokens=500,
    )

    sql = completion.choices[0].message.content.strip()
    # Clean up any markdown formatting
    sql = sql.replace("```sql", "").replace("```", "").strip()

    logger.info("Generated SQL: %s", sql)

    # Execute the query
    result = query_sheet(sql, data_dir)

    if result["error"]:
        logger.warning("SQL error: %s — falling back to RAG", result["error"])
        # Try to fix the query once
        fix_completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Fix this SQLite query. Return ONLY the corrected SQL, nothing else.",
                },
                {
                    "role": "user",
                    "content": f"Schema:\n{schema_desc}\n\nFailed query: {sql}\nError: {result['error']}\n\nFixed SQL:",
                },
            ],
            temperature=0,
            max_tokens=500,
        )
        fixed_sql = fix_completion.choices[0].message.content.strip()
        fixed_sql = fixed_sql.replace("```sql", "").replace("```", "").strip()
        logger.info("Retrying with fixed SQL: %s", fixed_sql)
        result = query_sheet(fixed_sql, data_dir)
        sql = fixed_sql

        if result["error"]:
            # Give up on SQL, fall back to RAG
            return _answer_unstructured(question, matches, openai_client)

    # Format the result into a natural language answer
    columns = result["columns"]
    rows = result["rows"]

    if not rows:
        result_text = "The query returned no results."
    elif len(rows) == 1 and len(columns) == 1:
        result_text = f"Result: {rows[0][0]}"
    else:
        # Format as a readable table
        lines = [" | ".join(columns)]
        lines.append(" | ".join(["---"] * len(columns)))
        for row in rows[:50]:  # Limit to 50 rows
            lines.append(" | ".join(str(v) if v is not None else "" for v in row))
        result_text = "\n".join(lines)

    # Generate natural language answer from the query result
    answer_completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Answer the user's question based on the SQL query result below. "
                    "Be concise and precise. If the result is a number, state it clearly. "
                    "If it's a table, summarize the key points."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nSQL Query: {sql}\n\nResult:\n{result_text}",
            },
        ],
        temperature=0.2,
        max_tokens=1000,
    )

    answer = answer_completion.choices[0].message.content or result_text

    # Build sources from matches
    sources = _build_sources(matches)

    return AskResponse(answer=answer, sources=sources, method="sql", sql_query=sql)


def _answer_unstructured(question: str, matches: list, openai_client) -> AskResponse:
    """Standard RAG answer for unstructured documents."""
    context_parts = []
    for match in matches:
        metadata = match.get("metadata", {})
        text = metadata.get("text", "")
        title = metadata.get("title", "")
        context_parts.append(f"[Source: {title}]\n{text}")

    context = "\n\n---\n\n".join(context_parts)

    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions based on the provided context. "
                    "Use ONLY the context below to answer. Do NOT mix information from unrelated documents. "
                    "If the context doesn't contain enough information, say so. "
                    "Cite the source document title when referencing information."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
        temperature=0.2,
        max_tokens=1000,
    )

    answer = completion.choices[0].message.content or "No answer generated."
    sources = _build_sources(matches)

    return AskResponse(answer=answer, sources=sources, method="rag")


def _build_sources(matches: list) -> list[Source]:
    sources = []
    for match in matches:
        metadata = match.get("metadata", {})
        sources.append(Source(
            title=metadata.get("title", ""),
            doc_id=metadata.get("doc_id", ""),
            url=metadata.get("url", ""),
            source_type=metadata.get("source_type", ""),
            chunk_index=metadata.get("chunk_index", 0),
            text=metadata.get("text", "")[:500],
            score=round(match.get("score", 0), 4),
        ))
    return sources
