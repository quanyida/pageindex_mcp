#!/usr/bin/env python3
"""PageIndex MCP Server - 标准 MCP 协议，兼容 Claude Desktop/Claude Code 等"""
from __future__ import annotations
import sys
import os
import json
import asyncio
import argparse
from pathlib import Path
from typing import Any

# Load .env file
try:
    from dotenv import load_dotenv
    # 优先加载 server.py 所在目录的 .env，再加载父目录的
    server_dir = Path(__file__).parent
    if (server_dir / ".env").exists():
        load_dotenv(server_dir / ".env")
    elif (server_dir.parent / ".env").exists():
        load_dotenv(server_dir.parent / ".env")
except ImportError:
    pass

# First import MCP SDK - no path conflicts when in subdirectory!
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add parent directory to path for pageindex
project_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, project_dir)

# Import PageIndex
from pageindex import PageIndexClient


class PageIndexMCPServer:
    def __init__(self, workspace=None):
        self.server = Server("pageindex")
        if workspace:
            self.workspace = Path(workspace).expanduser()
        else:
            # 默认使用相对于 server.py 的 ../data/ 目录
            self.workspace = Path(__file__).parent.parent / "data"
            self.workspace.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._register_tools()

    @property
    def client(self):
        if self._client is None:
            model = os.environ.get('MODEL', 'MiniMax-M2.5')
            self._client = PageIndexClient(model=model, workspace=self.workspace)
        return self._client

    def _get_full_doc(self, doc_id: str) -> dict | None:
        """Get full document with structure and pages loaded."""
        doc = self.client.documents.get(doc_id)
        if not doc:
            return None
        # Ensure full document is loaded
        self.client._ensure_doc_loaded(doc_id)
        return self.client.documents.get(doc_id)

    def _register_tools(self):
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="list_documents",
                    description="List all indexed documents",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="index_document",
                    description="Index a PDF or Markdown document",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string"},
                            "mode": {"type": "string", "enum": ["auto", "pdf", "md"]},
                            "engine": {"type": "string", "enum": ["pypdf2", "mineru"]}
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="get_document",
                    description="Get document metadata",
                    inputSchema={
                        "type": "object",
                        "properties": {"doc_id": {"type": "string"}},
                        "required": ["doc_id"]
                    }
                ),
                Tool(
                    name="get_document_structure",
                    description="Get document structure",
                    inputSchema={
                        "type": "object",
                        "properties": {"doc_id": {"type": "string"}},
                        "required": ["doc_id"]
                    }
                ),
                Tool(
                    name="get_page_content",
                    description="Get page content. pages format: '5-7' (range), '3,8' (multiple), '12' (single)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_id": {"type": "string"},
                            "pages": {"type": "string"}
                        },
                        "required": ["doc_id", "pages"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name, arguments):
            try:
                if name == "list_documents":
                    docs = []
                    for doc_id, doc in self.client.documents.items():
                        docs.append({
                            "doc_id": doc_id,
                            "doc_name": doc.get("doc_name", ""),
                            "doc_description": doc.get("doc_description", ""),
                            "type": doc.get("type", ""),
                            "page_count": doc.get("page_count"),
                            "line_count": doc.get("line_count")
                        })
                    return [TextContent(type="text", text=json.dumps(docs, ensure_ascii=False, indent=2))]

                elif name == "index_document":
                    file_path = arguments.get("file_path")
                    mode = arguments.get("mode", "auto")
                    engine = arguments.get("engine", "pypdf2")
                    if not os.path.exists(file_path):
                        return [TextContent(type="text", text=f"Error: File not found: {file_path}")]

                    import sys
                    from io import StringIO

                    # 临时抑制 print 输出，避免干扰 MCP JSON 协议
                    old_stdout = sys.stdout
                    sys.stdout = StringIO()

                    # 使用线程池
                    loop = asyncio.get_event_loop()
                    try:
                        doc_id = await loop.run_in_executor(
                            None,
                            lambda: self.client.index(file_path, mode, engine)
                        )
                    except Exception as e:
                        sys.stdout = old_stdout
                        return [TextContent(type="text", text=f"Error: {e}")]
                    finally:
                        sys.stdout = old_stdout

                    return [TextContent(type="text", text=json.dumps({
                        "status": "success",
                        "doc_id": doc_id,
                        "message": f"Document indexed: {doc_id}"
                    }, ensure_ascii=False, indent=2))]

                elif name == "get_document":
                    doc_id = arguments.get("doc_id")
                    if not doc_id:
                        return [TextContent(type="text", text="Error: doc_id is required")]
                    return [TextContent(type="text", text=self.client.get_document(doc_id))]

                elif name == "get_document_structure":
                    doc_id = arguments.get("doc_id")
                    if not doc_id:
                        return [TextContent(type="text", text="Error: doc_id is required")]
                    return [TextContent(type="text", text=self.client.get_document_structure(doc_id))]

                elif name == "get_page_content":
                    doc_id = arguments.get("doc_id")
                    pages = arguments.get("pages")
                    if not doc_id:
                        return [TextContent(type="text", text="Error: doc_id is required")]
                    if not pages:
                        return [TextContent(type="text", text="Error: pages is required")]
                    return [TextContent(type="text", text=self.client.get_page_content(doc_id, pages))]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=str, default=None)
    args = parser.parse_args()
    server = PageIndexMCPServer(workspace=args.workspace)
    asyncio.run(server.run())

if __name__ == "__main__":
    main()