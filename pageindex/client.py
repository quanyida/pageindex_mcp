from __future__ import annotations
import os
import uuid
import json
import asyncio
import concurrent.futures
from pathlib import Path
import shutil
import PyPDF2

from .page_index import page_index
from .page_index_md import md_to_tree


class PageIndexClient:
    def __init__(self, model=None, workspace=None):
        self.model = model or os.environ.get('MODEL', 'MiniMax-M2.5')
        self.workspace = Path(workspace) if workspace else None
        if self.workspace:
            self.workspace.mkdir(parents=True, exist_ok=True)
        self.documents = {}
        if self.workspace:
            self._load_workspace()

    def index(self, file_path: str, mode: str = "auto", engine: str = "mineru") -> str:
        """Index a document. Returns a document_id."""
        file_path = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        doc_id = str(uuid.uuid4())
        temp_dir = None  # mineru 临时目录
        ext = os.path.splitext(file_path)[1].lower()

        is_pdf = ext == '.pdf'
        is_md = ext in ['.md', '.markdown']

        # mineru 引擎：将 PDF 转 MD 后按 MD 处理
        if engine == "mineru" and is_pdf:
            import subprocess

            mineru_cmd = os.path.expanduser("~/.mineru/bin/mineru-open-api.exe")
            mineru_temp_dir = os.path.expanduser("~/.mineru/temp")
            os.makedirs(mineru_temp_dir, exist_ok=True)

            # 输出目录：用原始 PDF 文件名
            pdf_name = os.path.splitext(os.path.basename(file_path))[0]
            md_out_dir = os.path.join(mineru_temp_dir, pdf_name)
            os.makedirs(md_out_dir, exist_ok=True)

            print(f"Extracting with mineru: {file_path}")

            md_out = os.path.join(md_out_dir, "mineru_output.md")
            cmd = f'"{mineru_cmd}" extract "{file_path}" -o "{md_out_dir}" -f md'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

            # 找生成的 MD 文件（文件名可能不同）
            md_files = list(Path(md_out_dir).glob("*.md"))
            if not md_files:
                raise RuntimeError(f"mineru failed: no md file found")
            md_out = md_files[0]
            print(f"mineru extracted: {md_out}")

            # 切换为 MD 模式
            file_path = str(md_out)
            is_pdf = False
            is_md = True
            mode = "md"
            temp_dir = md_out_dir

        if mode == "pdf" or (mode == "auto" and is_pdf):
            print(f"Indexing PDF: {file_path}")
            result = page_index(
                doc=file_path,
                model=self.model,
                if_add_node_summary='yes',
                if_add_node_text='yes',
                if_add_node_id='yes',
                if_add_doc_description='yes'
            )
            pages = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for i, page in enumerate(pdf_reader.pages, 1):
                    pages.append({'page': i, 'content': page.extract_text() or ''})

            self.documents[doc_id] = {
                'id': doc_id,
                'type': 'pdf',
                'path': file_path,
                'doc_name': result.get('doc_name', ''),
                'doc_description': result.get('doc_description', ''),
                'page_count': len(pages),
                'structure': result['structure'],
                'pages': pages,
            }

        elif mode == "md" or (mode == "auto" and is_md):
            print(f"Indexing Markdown: {file_path}")
            coro = md_to_tree(
                md_path=file_path,
                if_thinning=False,
                if_add_node_summary='yes',
                summary_token_threshold=200,
                model=self.model,
                if_add_doc_description='yes',
                if_add_node_text='yes',
                if_add_node_id='yes'
            )
            try:
                asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(asyncio.run, coro).result()
            except RuntimeError:
                result = asyncio.run(coro)
            self.documents[doc_id] = {
                'id': doc_id,
                'type': 'md',
                'path': file_path,
                'doc_name': result.get('doc_name', ''),
                'doc_description': result.get('doc_description', ''),
                'line_count': result.get('line_count', 0),
                'structure': result['structure'],
            }
        else:
            raise ValueError(f"Unsupported file format for: {file_path}")

        print(f"Indexing complete. Document ID: {doc_id}")
        # 删除 mineru 临时目录
        if engine == "mineru" and temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"Cleaned up: {temp_dir}")

        if self.workspace:
            self._save_doc(doc_id)
        return doc_id

    def get_document(self, doc_id: str) -> str:
        doc = self.documents.get(doc_id)
        if not doc:
            self._ensure_doc_loaded(doc_id)
            doc = self.documents.get(doc_id)
        if not doc:
            return json.dumps({"error": f"Document {doc_id} not found"})

        return json.dumps({
            "id": doc.get("id"),
            "doc_name": doc.get("doc_name"),
            "doc_description": doc.get("doc_description"),
            "page_count": doc.get("page_count"),
            "line_count": doc.get("line_count"),
            "type": doc.get("type")
        }, ensure_ascii=False, indent=2)

    def get_document_structure(self, doc_id: str) -> str:
        self._ensure_doc_loaded(doc_id)
        doc = self.documents.get(doc_id)
        if not doc:
            return json.dumps({"error": f"Document {doc_id} not found"})
        return json.dumps({"structure": doc.get("structure", [])}, ensure_ascii=False, indent=2)

    def get_page_content(self, doc_id: str, pages: str = "1") -> str:
        self._ensure_doc_loaded(doc_id)
        doc = self.documents.get(doc_id)
        if not doc:
            return json.dumps({"error": f"Document {doc_id} not found"})

        doc_type = doc.get("type")

        if doc_type == "md":
            lines = doc.get("structure", [])
            page_nums = self._parse_page_spec(pages, doc.get("line_count", 0))
            content_lines = []
            for i in page_nums:
                if i - 1 < len(lines):
                    content_lines.append(lines[i - 1].get("text", ""))
            content = "\n".join(content_lines)
        else:
            page_list = doc.get("pages", [])
            page_nums = self._parse_page_spec(pages, doc.get("page_count", 0))
            content_pages = []
            for i in page_nums:
                if i - 1 < len(page_list):
                    content_pages.append(page_list[i - 1].get("content", ""))
            content = "\n".join(content_pages)

        return json.dumps({"content": content}, ensure_ascii=False, indent=2)

    def _ensure_doc_loaded(self, doc_id: str):
        if doc_id in self.documents and self.workspace:
            doc = self.documents[doc_id]
            if doc.get("structure") is None or doc.get("pages") is None:
                path = self.workspace / f"{doc_id}.json"
                if path.exists():
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    self.documents[doc_id].update(data)

    def _parse_page_spec(self, spec: str, max_pages: int) -> list[int]:
        pages = []
        for part in spec.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                pages.extend(range(int(start), int(end) + 1))
            else:
                pages.append(int(part))
        return [p for p in pages if 1 <= p <= max_pages]

    def _load_workspace(self):
        if not self.workspace:
            return
        for path in self.workspace.glob("*.json"):
            if path.name == "_meta.json":
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                doc_id = data.get("id")
                if doc_id:
                    self.documents[doc_id] = data
            except:
                pass

    META_INDEX = "_meta.json"

    def _save_meta(self, doc_id: str, entry: dict):
        meta = {}
        meta_path = self.workspace / self.META_INDEX
        if meta_path.exists():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
            except:
                pass
        meta[doc_id] = entry
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _make_meta_entry(doc: dict) -> dict:
        entry = {
            'type': doc.get('type', ''),
            'doc_name': doc.get('doc_name', ''),
            'doc_description': doc.get('doc_description', ''),
            'path': doc.get('path', ''),
        }
        if doc.get('type') == 'pdf':
            entry['page_count'] = doc.get('page_count')
        elif doc.get('type') == 'md':
            entry['line_count'] = doc.get('line_count')
        return entry

    def _save_doc(self, doc_id: str):
        doc = self.documents[doc_id].copy()
        from .utils import remove_fields
        if doc.get("structure") and doc.get("type") == "pdf":
            doc["structure"] = remove_fields(doc.get("structure", []), fields=["text"])
        path = self.workspace / f"{doc_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        self._save_meta(doc_id, self._make_meta_entry(doc))
        self.documents[doc_id].pop("structure", None)
        self.documents[doc_id].pop("pages", None)