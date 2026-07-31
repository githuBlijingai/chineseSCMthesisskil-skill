#!/usr/bin/env python3
"""
CNKI MCP 客户端模块

为 chinese-thesis-workbench-skill 提供调用 cnki-mcp 服务器的能力。
支持自动启动 MCP 服务器、工具调用、异常处理和结果缓存。
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cnki_mcp_client")


@dataclass
class CNKIPaper:
    """CNKI 论文数据结构"""
    title: str
    url: str
    authors: list[str]
    source: str
    date: str
    cited_count: str
    download_count: str
    abstract: str = ""
    keywords: list[str] = None
    institutions: list[str] = None
    year: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    fund: str = ""
    inferred_type: str = ""
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.institutions is None:
            self.institutions = []
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "authors": self.authors,
            "source": self.source,
            "date": self.date,
            "cited_count": self.cited_count,
            "download_count": self.download_count,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "institutions": self.institutions,
            "year": self.year,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "doi": self.doi,
            "fund": self.fund,
            "inferred_type": self.inferred_type,
        }
    
    @classmethod
    def from_search_result(cls, data: dict) -> "CNKIPaper":
        """从搜索结果创建对象"""
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            authors=data.get("authors", []),
            source=data.get("source", ""),
            date=data.get("date", ""),
            cited_count=data.get("cited_count", "0"),
            download_count=data.get("download_count", "0"),
        )


class CNKIMCPClient:
    """
    CNKI MCP 客户端
    
    通过 stdio 与 cnki-mcp 服务器通信，提供同步 API。
    """
    
    def __init__(self, server_command: str):
        """
        初始化客户端
        
        Args:
            server_command: 启动 MCP 服务器的命令
        """
        self.server_command = server_command
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        
    def start(self) -> bool:
        """
        启动 MCP 服务器进程
        
        Returns:
            是否成功启动
        """
        try:
            logger.info(f"Starting CNKI MCP server: {self.server_command}")
            
            # 解析命令
            args = self.server_command.split()
            
            # 启动子进程
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            
            # 等待服务器初始化
            time.sleep(3)
            
            # 检查进程是否存活
            if self.process.poll() is not None:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                logger.error(f"MCP server failed to start: {stderr}")
                return False
            
            logger.info("CNKI MCP server started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False
    
    def stop(self):
        """停止 MCP 服务器进程"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("CNKI MCP server stopped")
            except Exception as e:
                logger.warning(f"Error stopping MCP server: {e}")
                try:
                    self.process.kill()
                except:
                    pass
    
    def _send_request(self, method: str, params: dict) -> dict:
        """
        发送 MCP 请求并获取响应
        
        注意：cnki-mcp 使用 FastMCP 2.0，工具参数中包含 ctx: Context 作为第二个参数，
        但 MCP 协议会自动注入上下文，用户只需要提供普通参数。
        
        Args:
            method: 工具名称
            params: 参数（不需要包含 ctx）
            
        Returns:
            响应结果
        """
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP server is not running")
        
        self._request_id += 1
        
        # MCP 协议：使用 tools/call 方法
        # FastMCP 2.0 格式
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": method,
                "arguments": params
            }
        }
        
        # 发送请求
        request_line = json.dumps(request, ensure_ascii=False) + "\n"
        logger.debug(f"Sending request: {request_line.strip()}")
        
        self.process.stdin.write(request_line)
        self.process.stdin.flush()
        
        # 读取响应
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")
        
        logger.debug(f"Received response: {response_line.strip()}")
        
        response = json.loads(response_line)
        
        if "error" in response:
            error_info = response['error']
            logger.error(f"MCP error: {error_info}")
            raise RuntimeError(f"MCP error: {error_info}")
        
        return response.get("result", {})
    
    def search_papers(
        self,
        query: str,
        search_type: str = "主题",
        pages: int = 1,
        sort: str = "相关度"
    ) -> list[CNKIPaper]:
        """
        搜索 CNKI 论文
        
        Args:
            query: 搜索关键词
            search_type: 搜索类型（主题、关键词、篇名等）
            pages: 搜索页数
            sort: 排序方式（相关度、发表时间、被引、下载、综合）
            
        Returns:
            论文列表
        """
        try:
            # 构建参数 - 使用 cnki-mcp 支持的格式
            params = {
                "query": query,
                "search_type": search_type,
                "pages": pages,
            }
            
            # 排序参数可选
            if sort and sort != "相关度":
                params["sort"] = sort
            
            logger.info(f"Search params: {params}")
            result = self._send_request("search_cnki", params)
            
            # 解析结果 - 处理两种可能的返回格式
            # 格式1: result 直接包含 papers
            if isinstance(result, dict) and "papers" in result:
                papers_data = result.get("papers", [])
                return [CNKIPaper.from_search_result(p) for p in papers_data]
            
            # 格式2: result.content[0].text 包含 JSON
            content = result.get("content", [])
            if content and len(content) > 0:
                text = content[0].get("text", "{}")
                try:
                    data = json.loads(text)
                    papers_data = data.get("papers", [])
                    return [CNKIPaper.from_search_result(p) for p in papers_data]
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse search result text: {text[:100]}")
            
            return []
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_paper_detail(self, url: str) -> Optional[CNKIPaper]:
        """
        获取论文详情
        
        Args:
            url: 论文详情页 URL
            
        Returns:
            论文详情对象，失败返回 None
        """
        try:
            result = self._send_request("get_paper_detail", {"url": url})
            
            # 处理两种可能的返回格式
            data = None
            
            # 格式1: result 直接包含论文数据
            if isinstance(result, dict) and "title" in result:
                data = result
            else:
                # 格式2: result.content[0].text 包含 JSON
                content = result.get("content", [])
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse detail text: {text[:100]}")
                        return None
            
            if not data:
                return None
            
            if data.get("isError"):
                logger.error(f"Get detail error: {data.get('error')}")
                return None
            
            return CNKIPaper(
                title=data.get("title", ""),
                url=url,
                authors=data.get("authors", []),
                source=data.get("source", ""),
                date=data.get("year", ""),
                cited_count=data.get("cited_count", "0"),
                download_count=data.get("download_count", "0"),
                abstract=data.get("abstract", ""),
                keywords=data.get("keywords", []),
                institutions=data.get("institutions", []),
                year=data.get("year", ""),
                volume=data.get("volume", ""),
                issue=data.get("issue", ""),
                pages=data.get("pages", ""),
                doi=data.get("doi", ""),
                fund=data.get("fund", ""),
            )
            
        except Exception as e:
            logger.error(f"Get detail failed: {e}")
            return None
    
    def find_best_match(self, query: str) -> Optional[CNKIPaper]:
        """
        查找最佳匹配的论文
        
        Args:
            query: 论文标题或关键词
            
        Returns:
            最佳匹配的论文，失败返回 None
        """
        try:
            result = self._send_request("find_best_match", {"query": query})
            
            # 处理两种可能的返回格式
            data = None
            
            # 格式1: result 直接包含数据
            if isinstance(result, dict) and "best_match" in result:
                data = result
            else:
                # 格式2: result.content[0].text 包含 JSON
                content = result.get("content", [])
                if content and len(content) > 0:
                    text = content[0].get("text", "{}")
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse match text: {text[:100]}")
                        return None
            
            if not data:
                return None
            
            best_match = data.get("best_match")
            if best_match and "url" in best_match:
                return self.get_paper_detail(best_match["url"])
            
            return None
            
        except Exception as e:
            logger.error(f"Find best match failed: {e}")
            return None


class CNKIPoolBuilder:
    """
    CNKI 文献池构建器
    
    根据配置自动检索、过滤、格式化文献。
    """
    
    def __init__(
        self,
        server_command: str,
        keywords: list[str],
        max_results: int = 10,
        min_citations: int = 0,
        year_range: Optional[tuple[int, int]] = None
    ):
        self.server_command = server_command
        self.keywords = keywords
        self.max_results = max_results
        self.min_citations = min_citations
        self.year_range = year_range
        self.papers: list[CNKIPaper] = []
        
    def build(self) -> list[CNKIPaper]:
        """
        构建文献池
        
        Returns:
            过滤后的论文列表
        """
        client = CNKIMCPClient(self.server_command)
        
        try:
            # 启动服务器
            if not client.start():
                logger.error("Failed to start CNKI MCP server, skipping CNKI search")
                return []
            
            # 对每个关键词进行搜索
            all_papers: dict[str, CNKIPaper] = {}  # 用 url 去重
            
            for keyword in self.keywords:
                logger.info(f"Searching CNKI for: {keyword}")
                papers = client.search_papers(
                    query=keyword,
                    pages=1,
                    sort="被引"  # 按被引数排序，优先高质量文献
                )
                
                for paper in papers[:self.max_results]:
                    if paper.url and paper.url not in all_papers:
                        # 获取详情
                        detail = client.get_paper_detail(paper.url)
                        if detail:
                            all_papers[paper.url] = detail
                        else:
                            all_papers[paper.url] = paper
                
                # 避免请求过快
                time.sleep(2)
            
            # 过滤
            filtered = self._filter_papers(list(all_papers.values()))
            self.papers = filtered
            
            logger.info(f"CNKI pool built: {len(filtered)} papers")
            return filtered
            
        finally:
            client.stop()
    
    def _filter_papers(self, papers: list[CNKIPaper]) -> list[CNKIPaper]:
        """过滤论文"""
        filtered = []
        
        for paper in papers:
            # 被引数过滤
            try:
                cited = int(paper.cited_count) if paper.cited_count else 0
                if cited < self.min_citations:
                    continue
            except:
                pass
            
            # 年份过滤
            if self.year_range and paper.year:
                try:
                    year = int(paper.year)
                    if year < self.year_range[0] or year > self.year_range[1]:
                        continue
                except:
                    pass
            
            filtered.append(paper)
        
        # 按被引数排序
        filtered.sort(key=lambda p: int(p.cited_count) if p.cited_count and p.cited_count.isdigit() else 0, reverse=True)
        
        return filtered
    
    def save_to_json(self, output_path: Path):
        """保存到 JSON 文件"""
        data = {
            "source": "cnki",
            "total": len(self.papers),
            "papers": [p.to_dict() for p in self.papers]
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved CNKI pool to: {output_path}")
    
    def generate_references(self, style: str = "gb7714") -> list[str]:
        """
        生成参考文献格式
        
        Args:
            style: 格式类型（gb7714）
            
        Returns:
            格式化后的参考文献列表
        """
        references = []
        
        for i, paper in enumerate(self.papers, 1):
            if style == "gb7714":
                ref = self._format_gb7714(paper)
                references.append(f"[{i}] {ref}")
        
        return references
    
    def _format_gb7714(self, paper: CNKIPaper) -> str:
        """格式化为 GB/T 7714 格式"""
        authors = ", ".join(paper.authors) if paper.authors else "佚名"
        title = paper.title
        source = paper.source
        year = paper.year or paper.date[:4] if paper.date else ""
        volume = paper.volume
        issue = paper.issue
        pages = paper.pages
        
        # 期刊论文格式: 作者. 题名[J]. 刊名, 年, 卷(期): 页码.
        if volume and issue:
            return f"{authors}. {title}[J]. {source}, {year}, {volume}({issue}): {pages}."
        elif year:
            return f"{authors}. {title}[J]. {source}, {year}."
        else:
            return f"{authors}. {title}[J]. {source}."


def main():
    """命令行测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CNKI MCP Client")
    parser.add_argument("--server", default="uvx --from git+https://github.com/h-lu/cnki-mcp cnki-mcp")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--output", help="Output JSON file path")
    
    args = parser.parse_args()
    
    # 构建文献池
    builder = CNKIPoolBuilder(
        server_command=args.server,
        keywords=[args.keyword],
        max_results=5,
        min_citations=0
    )
    
    papers = builder.build()
    
    print(f"\nFound {len(papers)} papers:")
    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}] {paper.title}")
        print(f"    作者: {', '.join(paper.authors)}")
        print(f"    来源: {paper.source}")
        print(f"    被引: {paper.cited_count}")
    
    # 保存
    if args.output:
        builder.save_to_json(Path(args.output))
    
    # 打印参考文献
    print("\n\nReferences (GB/T 7714):")
    for ref in builder.generate_references():
        print(ref)


if __name__ == "__main__":
    main()
