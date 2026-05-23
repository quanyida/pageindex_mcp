# PageIndex MCP Server v1.0.0

标准 MCP 服务器 - 兼容 Claude Code 和其他 MCP 客户端！

## 特点

✅ 标准 MCP 协议 - 兼容所有 MCP 客户端
✅ 完全独立 - 所有依赖和数据都在本地
✅ 不污染系统环境 - 删除文件夹即彻底卸载
✅ 自动加载 .env 配置

## 快速开始

### 1. 创建虚拟环境并安装依赖

> **注意：** 此 MCP 依赖 [MinerU OpenAPI](https://github.com/opendatalab/MinerU-Ecosystem) 进行 PDF OCR 和解析。请先按照其文档部署 MinerU OpenAPI 服务。

```bash
# 创建虚拟环境
python -m venv venv

# 激活并安装依赖 (Windows)
venv\Scripts\pip install -r requirements.txt

# 激活并安装依赖 (Linux/Mac)
venv/bin/pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的配置：

```
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://ark.cn-beijing.volces.com/api/coding/v3
MODEL=MiniMax-M2.5
```

### 3. 配置客户端

---

## 客户端支持

### Claude Code (命令行)

在 Claude Code 中添加 MCP 服务器：

```bash
claude mcp add pageindex "D:\\develop\\github-projects\\PageIndex\\venv\\Scripts\\python.exe" "D:\\develop\\github-projects\\PageIndex\\pageindex-mcp\\mcp_server\\server.py"
```

或在 `settings.json` 中配置：

```json
{
  "mcpServers": {
    "pageindex": {
      "command": "D:\\develop\\github-projects\\PageIndex\\venv\\Scripts\\python.exe",
      "args": [
        "D:\\develop\\github-projects\\PageIndex\\pageindex-mcp\\mcp_server\\server.py"
      ]
    }
  }
}
```

查看 `config-templates/` 目录获取配置示例。

---

## 目录结构

```
pageindex-mcp/
├── pageindex/            # PageIndex 核心库
├── mcp_server/          # MCP 服务器
├── pageindex-qa-skill/ # Agentic RAG skill
├── data/                # 索引数据存储
├── venv/                # Python 虚拟环境
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
└── README.md          # 本文档
```

## 使用方法

在支持 MCP 的客户端中使用：

- "List my documents" （列出文档）
- "Index this PDF: /path/to/file.pdf" （索引文档）
- "Get page 1-5 of doc-id" （获取页面内容）
- "Search for '关键词' in all documents" （搜索）

## 可用工具

| 工具名 | 说明 |
|--------|------|
| `list_documents` | 列出所有已索引的文档 |
| `index_document` | 索引新的 PDF 或 Markdown 文档 |
| `get_document` | 获取文档元数据 |
| `get_document_structure` | 获取文档结构 |
| `get_page_content` | 获取指定页面内容 |
| `search_document` | 在单个文档中搜索关键词 |
| `search_all_documents` | 在所有文档中搜索关键词 |

## 搜索提示

- 用简短关键词搜索，如 "算电协同"
- 或者让 AI 先看文档结构，再获取相关内容（Agentic RAG）

## 卸载

```bash
# 从 Claude 中移除
claude mcp remove pageindex

# 删除整个文件夹
```

## 注意事项

- Python 版本需要 >= 3.9
- 确保已正确配置 .env 文件
- 所有数据都在 data 目录，删除前请备份
