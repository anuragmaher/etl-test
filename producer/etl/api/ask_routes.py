"""Agentic RAG Q&A — ReAct loop with tools for SQL queries and document search."""

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from etl.storage.store import load_pinecone_config, is_pinecone_configured
from etl.output.sheet_store import list_tables, query_sheet

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ask"])

MAX_AGENT_STEPS = 8


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


class AgentStep(BaseModel):
    thought: str
    tool: str
    tool_input: str
    result: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    method: str = ""
    sql_query: str = ""
    steps: list[AgentStep] = []


# Tool definitions for the agent
TOOLS_DESCRIPTION = """You have access to the following tools:

1. search_documents(query: str) — Search synced documents (Google Docs, PDFs, DOCX, Notion pages) using semantic search. Returns the most relevant text chunks. Use this for unstructured data like policies, questionnaires, meeting notes, etc.

2. sql_query(sql: str) — Execute a SQL query against the spreadsheet database. Use this for structured data like employee lists, financial data, etc. Returns rows and columns.

3. list_tables() — List all available tables in the spreadsheet database with their column names and types. Call this BEFORE writing SQL to see the schema.

4. final_answer(answer: str) — Provide the final answer to the user. You MUST call this tool to end the conversation.

IMPORTANT RULES:
- Always call list_tables() before writing any SQL query
- You can use multiple tools in sequence to gather information
- You can combine data from both search_documents and sql_query
- If a SQL query fails, check the error and try a corrected query
- When you have enough information, call final_answer with a clear, concise answer
- Cite source documents when using information from search_documents"""


def _build_system_prompt():
    return f"""You are an intelligent assistant that answers questions by using tools to find information.
You follow the ReAct pattern: Thought → Action → Observation → repeat until you can answer.

{TOOLS_DESCRIPTION}

Respond in this exact JSON format for each step:
{{
  "thought": "your reasoning about what to do next",
  "tool": "tool_name",
  "tool_input": "the input to the tool"
}}

For final_answer, use:
{{
  "thought": "I now have enough information to answer",
  "tool": "final_answer",
  "tool_input": "your complete answer here"
}}"""


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Agentic Q&A using ReAct loop with tools."""
    if not is_pinecone_configured():
        raise HTTPException(status_code=400, detail="Pinecone not configured.")

    pc_config = load_pinecone_config()

    try:
        from openai import OpenAI
        from pinecone import Pinecone

        openai_client = OpenAI(api_key=pc_config["openai_api_key"])
        pc = Pinecone(api_key=pc_config["api_key"])
        index = pc.Index(pc_config["index_name"])

        # Resolve follow-ups
        resolved_question = request.question
        if request.history:
            history_text = "\n".join(
                f"{m.role}: {m.content}" for m in request.history[-6:]
            )
            resolve = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Rewrite the follow-up as a standalone question. Return ONLY the question."},
                    {"role": "user", "content": f"Conversation:\n{history_text}\n\nFollow-up: {request.question}\n\nStandalone question:"},
                ],
                temperature=0, max_tokens=200,
            )
            resolved_question = resolve.choices[0].message.content.strip()
            logger.info("Resolved: '%s' → '%s'", request.question, resolved_question)

        # Run the agent loop
        messages = [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": resolved_question},
        ]

        all_sources = []
        all_steps = []
        sql_queries = []
        methods_used = set()

        for step_num in range(MAX_AGENT_STEPS):
            completion = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            response_text = completion.choices[0].message.content
            messages.append({"role": "assistant", "content": response_text})

            try:
                action = json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning("Agent returned non-JSON: %s", response_text)
                break

            thought = action.get("thought", "")
            tool = action.get("tool", "")
            tool_input = action.get("tool_input", "")

            logger.info("Agent step %d: thought='%s', tool='%s'", step_num + 1, thought[:80], tool)

            # Execute the tool
            if tool == "final_answer":
                all_steps.append(AgentStep(thought=thought, tool=tool, tool_input=str(tool_input), result=""))
                method = " + ".join(sorted(methods_used)) if methods_used else "agent"
                sql_query = "; ".join(sql_queries) if sql_queries else ""
                return AskResponse(
                    answer=str(tool_input),
                    sources=all_sources,
                    method=method,
                    sql_query=sql_query,
                    steps=all_steps,
                )

            elif tool == "search_documents":
                methods_used.add("rag")
                observation, sources = _tool_search_documents(
                    str(tool_input), openai_client, index
                )
                all_sources.extend(sources)

            elif tool == "sql_query":
                methods_used.add("sql")
                sql_queries.append(str(tool_input))
                observation = _tool_sql_query(str(tool_input))

            elif tool == "list_tables":
                observation = _tool_list_tables()

            else:
                observation = f"Unknown tool: {tool}"

            all_steps.append(AgentStep(
                thought=thought, tool=tool,
                tool_input=str(tool_input), result=observation[:500],
            ))

            # Feed observation back to agent
            messages.append({"role": "user", "content": f"Observation:\n{observation}"})

        # If we hit the step limit
        return AskResponse(
            answer="I wasn't able to find a complete answer within the allowed steps.",
            sources=all_sources,
            method="agent",
            steps=all_steps,
        )

    except Exception as e:
        logger.exception("Agent failed")
        raise HTTPException(status_code=500, detail=str(e))


def _tool_search_documents(query: str, openai_client, index) -> tuple:
    """Search Pinecone for relevant document chunks."""
    embed = openai_client.embeddings.create(
        model="text-embedding-3-large", input=[query],
    )
    vector = embed.data[0].embedding

    results = index.query(vector=vector, top_k=5, include_metadata=True)
    matches = results.get("matches", [])

    if not matches:
        return "No relevant documents found.", []

    sources = []
    context_parts = []
    for match in matches:
        meta = match.get("metadata", {})
        text = meta.get("text", "")
        title = meta.get("title", "")
        score = match.get("score", 0)

        sources.append(Source(
            title=title,
            doc_id=meta.get("doc_id", ""),
            url=meta.get("url", ""),
            source_type=meta.get("source_type", ""),
            chunk_index=meta.get("chunk_index", 0),
            text=text[:500],
            score=round(score, 4),
        ))
        context_parts.append(f"[Source: {title} (score: {score:.3f})]\n{text}")

    return "\n\n---\n\n".join(context_parts), sources


def _tool_sql_query(sql: str) -> str:
    """Execute SQL against the sheets database."""
    sql = sql.replace("```sql", "").replace("```", "").strip()
    result = query_sheet(sql, "./data")

    if result["error"]:
        return f"SQL Error: {result['error']}"

    columns = result["columns"]
    rows = result["rows"]

    if not rows:
        return "Query returned no results."

    if len(rows) == 1 and len(columns) == 1:
        return f"Result: {rows[0][0]}"

    lines = [" | ".join(str(c) for c in columns)]
    lines.append(" | ".join(["---"] * len(columns)))
    for row in rows[:50]:
        lines.append(" | ".join(str(v) if v is not None else "" for v in row))
    return "\n".join(lines)


def _tool_list_tables() -> str:
    """List available tables and their schemas."""
    tables = list_tables("./data")
    if not tables:
        return "No spreadsheet tables available in the database."

    parts = []
    for t in tables:
        cols = ", ".join([f'"{name}" ({dtype})' for name, dtype in t["columns"]])
        parts.append(f'Table: "{t["table_name"]}" ({t["row_count"]} rows)\n  Columns: {cols}')
    return "\n\n".join(parts)
