#!/usr/bin/env python3
"""
CNKI 直接爬虫模块 (Playwright 版本)

为 chinese-thesis-workbench-skill 提供直接的 CNKI 论文搜索能力。
无需 MCP 层，使用 Playwright 进行爬取，自动管理浏览器下载。

特性:
- 自动下载浏览器: 首次运行时自动从国内CDN下载Chromium
- 浏览器复用: 首次调用时启动浏览器，后续复用同一实例
- 超时刷新: 浏览器 10 分钟无活动后自动关闭，下次调用重新启动
- 线程安全: 使用锁保证并发安全
- 更好的反爬: Playwright 的反检测能力更强
"""

from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

# Playwright 相关导入
try:
    from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger("cnki_crawler")


# =================== 本地浏览器检测 ===================

def find_local_browser() -> Optional[str]:
    """
    检测本地已安装的浏览器路径
    优先顺序: Chrome > Edge > Firefox
    返回浏览器可执行文件路径，如果没找到返回None
    """
    # Chrome 常见安装路径
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(x86)%\Google\Chrome\Application\chrome.exe"),
    ]
    
    # Edge 常见安装路径
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
    ]
    
    # Firefox 常见安装路径
    firefox_paths = [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        os.path.expandvars(r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"),
    ]
    
    all_paths = [
        ("Chrome", chrome_paths),
        ("Edge", edge_paths),
        ("Firefox", firefox_paths),
    ]
    
    for browser_name, paths in all_paths:
        for path in paths:
            if os.path.exists(path):
                logger.info(f"找到本地浏览器: {browser_name} ({path})")
                return path
    
    logger.warning("未找到本地安装的浏览器 (Chrome/Edge/Firefox)")
    return None


# =================== 自定义异常 ===================

class CNKIError(Exception):
    """CNKI 服务基础异常"""
    pass


class BrowserError(CNKIError):
    """浏览器相关错误"""
    pass


class SearchError(CNKIError):
    """搜索相关错误"""
    pass


# =================== 数据模型 ===================

@dataclass
class CNKIPaper:
    """CNKI 论文数据结构"""
    title: str = ""
    url: str = ""
    authors: List[str] = field(default_factory=list)
    source: str = ""
    date: str = ""
    cited_count: str = "0"
    download_count: str = "0"
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    institutions: List[str] = field(default_factory=list)
    year: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    fund: str = ""
    classification: str = ""
    inferred_type: str = ""  # 推断的文献类型（期刊/学位/会议等）
    
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
            "classification": self.classification,
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


# =================== 配置参数 ===================

SEARCH_TYPES = {
    "主题": "SU",
    "篇关摘": "TKA",
    "关键词": "KY",
    "篇名": "TI",
    "全文": "FT",
    "作者": "AU",
    "第一作者": "FI",
    "通讯作者": "RP",
    "作者单位": "AF",
    "基金": "FU",
    "摘要": "AB",
    "参考文献": "RF",
    "分类号": "CLC",
    "文献来源": "LY",
    "DOI": "DOI",
}

SEARCH_TYPE_VALUES = {
    "主题": "SU$%=|",
    "篇关摘": "TKA$%=|",
    "关键词": "KY$=|",
    "篇名": "TI$%=|",
    "全文": "FT$%=|",
    "作者": "AU$=|",
    "第一作者": "FI$=|",
    "通讯作者": "RP$%=|",
    "作者单位": "AF$%",
    "基金": "FU$%|",
    "摘要": "AB$%=|",
    "参考文献": "RF$%=|",
    "分类号": "CLC$=|??",
    "文献来源": "LY$%=|",
    "DOI": "DOI$=|?",
}

SEARCH_TYPE_ALIASES = {
    "subject": "主题",
    "theme": "主题",
    "keyword": "关键词",
    "keywords": "关键词",
    "title": "篇名",
    "author": "作者",
    "first_author": "第一作者",
    "corresponding_author": "通讯作者",
    "affiliation": "作者单位",
    "institution": "作者单位",
    "fund": "基金",
    "abstract": "摘要",
    "fulltext": "全文",
    "reference": "参考文献",
    "source": "文献来源",
    "doi": "DOI",
}

SORT_TYPES = {
    "相关度": "FFD",
    "发表时间": "PT",
    "被引": "CF",
    "下载": "DFR",
    "综合": "ZH",
}

SORT_TYPE_ALIASES = {
    "relevance": "相关度",
    "date": "发表时间",
    "publish_time": "发表时间",
    "time": "发表时间",
    "cited": "被引",
    "citation": "被引",
    "citations": "被引",
    "download": "下载",
    "downloads": "下载",
    "composite": "综合",
    "general": "综合",
}

# =================== 文献类型优先级 ===================

LITERATURE_TYPE_PRIORITY = {
    "期刊论文": 1,
    "学位论文": 2,
    "会议论文": 3,
    "外文期刊": 4,
    "出版图书": 5,
    "标准": 6,
    "专利": 7,
}

# 优先检索的文献类型（按优先级排序）
DEFAULT_LITERATURE_TYPES = ["期刊论文", "学位论文", "会议论文", "外文期刊"]


def extract_tech_keywords_from_text(text: str) -> list[str]:
    """
    从技术文本中提取关键词
    
    提取模式：
    - 芯片型号（如 STM32F103C8T6）
    - 通信协议（如 I2C, SPI, USART）
    - 算法名称（如 PID, 神经网络）
    - 技术术语（如 嵌入式, 单片机）
    """
    if not text:
        return []
    
    import re
    
    # 技术模式定义
    patterns = {
        "chip": r"(STM32\w+|51单片机|ESP32\w+|Arduino\w+|AVR\w+|PIC\w+|MSP430\w+)",
        "protocol": r"(I2C|SPI|USART|UART|CAN|LIN|USB|Ethernet|RS-?485|RS-?232|Modbus|Bluetooth|Zigbee|Wi-?Fi|LoRa|NB-?IoT)",
        "algorithm": r"(PID|模糊控制|神经网络|深度学习|机器学习|遗传算法|蚁群算法|粒子群|卡尔曼滤波|FFT|小波变换)",
        "tech": r"(嵌入式|单片机|微控制器|传感器|执行器|物联网|IoT|智能家居|工业控制|自动化|实时操作系统|RTOS|华为LiteOS|FreeRTOS|UCOS)",
        "component": r"(DHT11|DS18B20|MPU6050|HC-SR04|HC-SR501|MQ-2|MQ-135|BMP280|OLED|LCD|LED|继电器|步进电机|伺服电机)",
    }
    
    keywords = []
    text_upper = text.upper()
    
    for pattern_name, pattern in patterns.items():
        matches = re.findall(pattern, text_upper, re.IGNORECASE)
        keywords.extend(matches)
    
    # 去重并保留原始大小写
    unique_keywords = []
    seen = set()
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw)
    
    return unique_keywords


def filter_papers_by_literature_type(papers: list[dict], target_types: list[str] = None) -> list[dict]:
    """
    按文献类型过滤论文
    
    Args:
        papers: 论文列表
        target_types: 目标文献类型列表，默认使用 DEFAULT_LITERATURE_TYPES
    
    Returns:
        过滤后的论文列表
    """
    if target_types is None:
        target_types = DEFAULT_LITERATURE_TYPES
    
    if not papers:
        return []
    
    filtered = []
    for paper in papers:
        paper_type = paper.get("literature_type", "")
        source = paper.get("source", "")
        
        # 根据来源判断文献类型
        inferred_type = None
        if "会议" in source or " proceedings" in source.lower():
            inferred_type = "会议论文"
        elif "大学" in source or "学院" in source or "硕士" in source or "博士" in source:
            inferred_type = "学位论文"
        elif "出版社" in source or " press" in source.lower():
            inferred_type = "出版图书"
        else:
            inferred_type = "期刊论文"
        
        paper["inferred_type"] = inferred_type
        
        # 如果匹配目标类型，保留
        if paper_type in target_types or inferred_type in target_types:
            filtered.append(paper)
    
    # 按优先级排序
    def get_priority(paper):
        t = paper.get("literature_type") or paper.get("inferred_type", "期刊论文")
        return LITERATURE_TYPE_PRIORITY.get(t, 99)
    
    filtered.sort(key=get_priority)
    
    return filtered


# =================== 浏览器池管理 ===================

class BrowserPool:
    """
    浏览器池 - 使用 Playwright 管理浏览器实例
    
    特性:
    - 优先使用本地浏览器: 自动检测 Chrome/Edge/Firefox，无需下载
    - 自动安装备用: 未找到本地浏览器时，自动下载 Chromium
    - 延迟初始化：首次调用时才启动浏览器
    - 实例复用：多次调用共享同一浏览器
    - 超时关闭：10 分钟无活动自动关闭，节省资源
    - 线程安全：使用锁保证并发访问安全
    """
    
    IDLE_TIMEOUT = 600  # 10 分钟无活动后关闭浏览器
    
    def __init__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise BrowserError("Playwright 未安装，无法使用 CNKI 爬虫功能。请运行: pip install playwright")
        
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._last_used: float = 0
        self._lock = threading.Lock()
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

    def _create_browser(self) -> tuple[Browser, Page]:
        """
        创建浏览器实例，优先使用本地浏览器
        带增强反检测配置
        """
        logger.info("正在启动浏览器...")
        
        try:
            self._playwright = sync_playwright().start()
            
            # 首先尝试检测本地浏览器
            local_browser_path = find_local_browser()
            browser = None
            browser_type = "Unknown"
            
            if local_browser_path:
                # 根据路径判断浏览器类型
                if 'chrome' in local_browser_path.lower():
                    browser_type = "Chrome"
                elif 'edge' in local_browser_path.lower() or 'msedge' in local_browser_path.lower():
                    browser_type = "Edge"
                elif 'firefox' in local_browser_path.lower():
                    browser_type = "Firefox"
                
                logger.info(f"使用本地{browser_type}浏览器: {local_browser_path}")
                
                # 通用启动参数
                launch_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
                
                try:
                    if browser_type == "Firefox":
                        # Firefox 使用 firefox.launch
                        browser = self._playwright.firefox.launch(
                            headless=True,
                            executable_path=local_browser_path,
                            args=launch_args
                        )
                    else:
                        # Chrome/Edge 使用 chromium.launch
                        browser = self._playwright.chromium.launch(
                            headless=True,
                            executable_path=local_browser_path,
                            args=launch_args
                        )
                    logger.info(f"本地{browser_type}浏览器启动成功")
                except Exception as local_e:
                    logger.warning(f"本地浏览器启动失败: {local_e}，尝试自动下载Chromium...")
                    browser = None
            
            # 如果没有找到本地浏览器或本地启动失败，尝试自动下载Chromium
            if browser is None:
                logger.info("未找到本地浏览器或启动失败，尝试自动下载Chromium（约100MB）...")
                try:
                    browser = self._playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins,site-per-process',
                            '--disable-site-isolation-trials',
                            '--disable-dev-shm-usage',
                            '--no-sandbox',
                        ]
                    )
                    logger.info("Chromium浏览器下载并启动成功")
                except Exception as download_e:
                    logger.error(f"自动下载Chromium失败: {download_e}")
                    raise BrowserError(
                        f"无法启动浏览器:\n"
                        f"1. 本地浏览器启动失败: {local_browser_path or '未找到'}\n"
                        f"2. 自动下载Chromium失败: {download_e}\n\n"
                        f"解决方案:\n"
                        f"- 确保已安装Chrome/Edge/Firefox浏览器\n"
                        f"- 或手动下载Chromium: playwright install chromium"
                    )
            
            # 创建新页面
            context = browser.new_context(
                user_agent=random.choice(self._user_agents),
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
            )
            
            # 添加反检测脚本
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
            """)
            
            page = context.new_page()
            logger.info("浏览器实例创建成功")
            return browser, page
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            raise BrowserError(f"浏览器启动失败: {e}")
    
    def _is_browser_alive(self) -> bool:
        """检查浏览器是否仍然可用"""
        if self._browser is None or self._page is None:
            return False
        try:
            # 尝试访问一个简单属性来检查浏览器状态
            _ = self._page.url
            return True
        except Exception:
            return False
    
    def get_page(self) -> Page:
        """
        获取浏览器页面（线程安全）
        
        - 如果没有实例或实例已失效，创建新实例
        - 如果超时未使用，先关闭旧实例再创建新实例
        - 更新最后使用时间
        """
        with self._lock:
            current_time = time.time()
            
            # 检查是否需要关闭超时的浏览器
            if self._browser is not None:
                if current_time - self._last_used > self.IDLE_TIMEOUT:
                    self._close_browser_internal()
                elif not self._is_browser_alive():
                    self._browser = None
                    self._page = None
            
            # 如果没有可用的浏览器，创建新实例
            if self._browser is None:
                self._browser, self._page = self._create_browser()
            
            self._last_used = current_time
            return self._page
    
    def _close_browser_internal(self):
        """内部关闭方法（不加锁）"""
        if self._browser is not None:
            try:
                self._browser.close()
                logger.info("浏览器已关闭")
            except Exception:
                pass
            self._browser = None
            self._page = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
    
    def close(self):
        """关闭浏览器（线程安全）"""
        with self._lock:
            self._close_browser_internal()
    
    def navigate_to_cnki(self) -> Page:
        """获取页面并导航到 CNKI 首页"""
        page = self.get_page()
        current_url = page.url
        
        # 如果不在 CNKI 首页，则导航过去
        if "cnki.net" not in current_url or "kns.cnki.net" in current_url:
            page.goto("https://www.cnki.net/", wait_until="networkidle")
            time.sleep(random.uniform(1, 2))
        
        return page


# =================== 全局浏览器池实例 ===================

_browser_pool: Optional[BrowserPool] = None
_pool_lock = threading.Lock()


def get_browser_pool() -> BrowserPool:
    """获取全局浏览器池实例（延迟初始化）"""
    global _browser_pool
    if _browser_pool is None:
        with _pool_lock:
            if _browser_pool is None:
                _browser_pool = BrowserPool()
    return _browser_pool


def close_browser_pool():
    """关闭全局浏览器池"""
    global _browser_pool
    if _browser_pool is not None:
        _browser_pool.close()
        _browser_pool = None


# =================== 工具函数 ===================

def resolve_search_type(search_type: str) -> str:
    """解析搜索类型，支持中文或英文别名"""
    if not search_type:
        return "主题"
    search_type_lower = search_type.lower().strip()
    if search_type_lower in SEARCH_TYPE_ALIASES:
        return SEARCH_TYPE_ALIASES[search_type_lower]
    if search_type in SEARCH_TYPES:
        return search_type
    return "主题"


def resolve_sort_type(sort_type: str) -> str:
    """解析排序类型，支持中文或英文别名"""
    if not sort_type:
        return "相关度"
    sort_type_lower = sort_type.lower().strip()
    if sort_type_lower in SORT_TYPE_ALIASES:
        return SORT_TYPE_ALIASES[sort_type_lower]
    if sort_type in SORT_TYPES:
        return sort_type
    return "相关度"


def select_search_type(page, search_type: str) -> bool:
    """在页面上选择搜索类型"""
    try:
        value = SEARCH_TYPE_VALUES.get(search_type)
        if not value:
            return False
        
        # 点击下拉框
        page.click("#DBFieldBox", timeout=10000)
        time.sleep(0.8)
        
        # 选择选项
        page.click(f'#DBFieldList a[value="{value}"]', timeout=10000)
        time.sleep(0.5)
        return True
    except Exception as e:
        logger.warning(f"选择搜索类型失败: {e}")
        return False


def apply_sort(page, sort_type: str) -> bool:
    """在搜索结果页面应用排序"""
    try:
        sort_id = SORT_TYPES.get(sort_type)
        if not sort_id:
            return False
        
        page.click(f"#{sort_id}", timeout=10000)
        time.sleep(random.uniform(1.5, 2.5))
        
        # 等待结果加载
        page.wait_for_selector('table.result-table-list tbody tr', timeout=15000)
        return True
    except Exception as e:
        logger.warning(f"应用排序失败: {e}")
        return False


def parse_paper_info(row_element, debug: bool = False) -> dict:
    """从搜索结果行中提取论文信息"""
    paper = {"title": "", "url": "", "authors": [], "source": "", "date": "", "cited_count": "0", "download_count": "0"}
    
    try:
        # 1. 提取标题
        title_selectors = [
            'a.fz14',
            'td.name a',
            'td[class*="name"] a',
            'a[href*="/kcms/detail/"]',
        ]
        for selector in title_selectors:
            try:
                elem = row_element.query_selector(selector)
                if elem:
                    text = elem.inner_text().strip()
                    if text:
                        paper["title"] = text
                        paper["url"] = elem.get_attribute("href") or ""
                        break
            except:
                continue
        
        # 2. 提取作者
        author_selectors = [
            'td.author a',
            'td[class*="author"] a',
            'span[class*="author"] a',
        ]
        for selector in author_selectors:
            try:
                elems = row_element.query_selector_all(selector)
                authors = [a.inner_text().strip() for a in elems if a.inner_text().strip()]
                if authors:
                    paper["authors"] = authors
                    break
            except:
                continue
        
        # 3. 提取来源
        source_selectors = [
            'td.source a',
            'td[class*="source"] a',
        ]
        for selector in source_selectors:
            try:
                elem = row_element.query_selector(selector)
                if elem:
                    text = elem.inner_text().strip()
                    if text:
                        paper["source"] = text
                        break
            except:
                continue
        
        # 4. 提取日期
        date_selectors = [
            'td.date',
            'td[class*="date"]',
            'span[class*="date"]',
        ]
        for selector in date_selectors:
            try:
                elem = row_element.query_selector(selector)
                if elem:
                    text = elem.inner_text().strip()
                    if text:
                        paper["date"] = text
                        break
            except:
                continue
        
        # 5. 提取被引次数
        cite_selectors = [
            'td.quote a',
            'td[class*="quote"] a',
            'td.quote',
            'span[class*="cite"]',
        ]
        for selector in cite_selectors:
            try:
                elem = row_element.query_selector(selector)
                if elem:
                    text = elem.inner_text().strip()
                    if text:
                        paper["cited_count"] = text
                        break
            except:
                continue
        
        # 6. 提取下载次数
        download_selectors = [
            'td.download a',
            'td[class*="download"] a',
            'td.download',
        ]
        for selector in download_selectors:
            try:
                elem = row_element.query_selector(selector)
                if elem:
                    text = elem.inner_text().strip()
                    if text:
                        paper["download_count"] = text
                        break
            except:
                continue
    except Exception as e:
        if debug:
            logger.debug(f"解析论文信息出错: {e}")
    
    return paper


def find_closest_title(title: str, result_titles: List[str]) -> int:
    """根据字符匹配度选择最接近的搜索结果"""
    max_similar = 0
    best_index = 0
    for i, t in enumerate(result_titles):
        common_chars = sum(c in t for c in title)
        if common_chars > max_similar:
            max_similar = common_chars
            best_index = i
    return best_index


# =================== 核心搜索函数 ===================

def search_cnki(
    query: str,
    search_type: str = "主题",
    pages: int = 1,
    sort: str = "相关度",
    debug: bool = False
) -> dict:
    """
    搜索 CNKI 论文
    
    Args:
        query: 搜索关键词
        search_type: 搜索类型（主题、关键词、作者、篇名等）
        pages: 搜索页数（每页约20条结果）
        sort: 排序方式（相关度、发表时间、被引、下载、综合）
        debug: 是否开启调试模式
    
    Returns:
        包含论文列表的字典: {"papers": [CNKIPaper, ...], "total_papers": int, ...}
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {"isError": True, "error": "Playwright 未安装，无法使用 CNKI 爬虫。请运行: pip install playwright && playwright install chromium", "papers": []}
    
    resolved_type = resolve_search_type(search_type)
    resolved_sort = resolve_sort_type(sort)
    all_papers = []
    
    try:
        pool = get_browser_pool()
        page = pool.navigate_to_cnki()
        
        # 选择搜索类型
        if resolved_type != "主题":
            select_search_type(page, resolved_type)
        
        # 输入搜索关键词
        page.fill("#txt_SearchText", query, timeout=15000)
        
        # 模拟人工输入延迟
        time.sleep(random.uniform(0.1, 0.3))
        
        # 点击搜索按钮
        page.click(".search-btn", timeout=15000)
        
        # 等待搜索结果加载
        time.sleep(random.uniform(3, 4))
        
        # 应用排序
        if resolved_sort != "相关度":
            apply_sort(page, resolved_sort)
        
        # 遍历每一页
        for page_num in range(1, pages + 1):
            try:
                # 等待结果表格加载
                page.wait_for_selector("table.result-table-list", timeout=20000)
                
                # 获取所有行
                rows = page.query_selector_all('table.result-table-list tbody tr')
                
                for row in rows:
                    paper_data = parse_paper_info(row, debug)
                    if paper_data["title"]:
                        paper_data["page"] = page_num
                        all_papers.append(paper_data)
                        
            except PlaywrightTimeout:
                logger.warning(f"第 {page_num} 页加载超时")
            except Exception as e:
                if debug:
                    logger.debug(f"解析第 {page_num} 页出错: {e}")
            
            # 翻页
            if page_num < pages:
                try:
                    next_btn = page.query_selector("#PageNext")
                    if next_btn and next_btn.is_enabled():
                        next_btn.click()
                        time.sleep(random.uniform(1.5, 2.5))
                    else:
                        break
                except Exception:
                    break
        
        return {
            "query": query,
            "search_type": resolved_type,
            "sort": resolved_sort,
            "total_pages": pages,
            "total_papers": len(all_papers),
            "papers": all_papers
        }
    
    except Exception as e:
        logger.error(f"搜索错误: {e}")
        return {"isError": True, "error": f"搜索错误: {str(e)}", "error_type": "SearchError", "papers": []}


def get_paper_detail(url: str) -> CNKIPaper:
    """
    获取 CNKI 论文详情页的完整信息
    
    Args:
        url: CNKI 论文详情页 URL
    
    Returns:
        CNKIPaper 对象
    """
    if not PLAYWRIGHT_AVAILABLE:
        return CNKIPaper(url=url, title="错误: Playwright 未安装")
    
    paper = CNKIPaper(url=url)
    
    try:
        pool = get_browser_pool()
        page = pool.get_page()
        page.goto(url, wait_until="networkidle")
        time.sleep(random.uniform(1.5, 2.5))
        
        # 标题
        try:
            paper.title = page.inner_text('div.wx-tit h1', timeout=5000).strip()
        except:
            try:
                paper.title = page.inner_text('h1', timeout=5000).strip()
            except:
                pass
        
        # 英文标题
        try:
            paper.title_en = page.inner_text('div.wx-tit h2', timeout=3000).strip()
        except:
            pass
        
        # 作者
        try:
            author_elems = page.query_selector_all('h3.author span a')
            paper.authors = [a.inner_text().strip() for a in author_elems if a.inner_text().strip()]
        except:
            pass
        
        # 机构
        try:
            org_elems = page.query_selector_all('h3.orgn span a')
            paper.institutions = [o.inner_text().strip() for o in org_elems if o.inner_text().strip()]
        except:
            pass
        
        # 摘要
        try:
            paper.abstract = page.inner_text('span#ChDivSummary', timeout=5000).strip()
        except:
            pass
        
        # 关键词
        try:
            keyword_elems = page.query_selector_all('p.keywords a')
            paper.keywords = [k.inner_text().strip().rstrip(';；') for k in keyword_elems if k.inner_text().strip()]
        except:
            pass
        
        # 来源
        try:
            paper.source = page.inner_text('div.top-tip a[href*="navi.cnki.net"]', timeout=5000).strip().rstrip(' .')
        except:
            pass
        
        # 年/卷/期/页
        try:
            info_text = page.inner_text('div.top-tip span', timeout=5000).strip()
            if ',' in info_text:
                parts = info_text.split(',')
                paper.year = parts[0].strip()
                if len(parts) > 1:
                    rest = parts[1]
                    if '(' in rest and ')' in rest:
                        paper.volume = rest.split('(')[0].strip()
                        paper.issue = rest.split('(')[1].split(')')[0].strip()
                    if ':' in rest:
                        paper.pages = rest.split(':')[-1].strip()
        except:
            pass
        
        # DOI
        try:
            paper.doi = page.inner_text('li.top-space:has-text("DOI") p', timeout=3000).strip()
        except:
            pass
        
        # 被引次数
        try:
            paper.cited_count = page.inner_text('span#refs a, div.total-inform span:has-text("被引") + em', timeout=3000).strip()
        except:
            pass
        
        # 下载次数
        try:
            paper.download_count = page.inner_text('span#DownLoadParts a, div.total-inform span:has-text("下载") + em', timeout=3000).strip()
        except:
            pass
        
        # 基金
        try:
            paper.fund = page.inner_text('li:has-text("基金") p, p.funds span', timeout=3000).strip()
        except:
            pass
        
        # 分类号
        try:
            paper.classification = page.inner_text('li:has-text("分类号") p', timeout=3000).strip()
        except:
            pass
        
        return paper
    
    except Exception as e:
        logger.error(f"获取详情错误: {e}")
        return CNKIPaper(url=url, title=f"获取详情错误: {str(e)}")


def find_best_match(query: str) -> Optional[CNKIPaper]:
    """
    快速查找与输入标题最匹配的 CNKI 论文
    
    Args:
        query: 论文标题或关键词
    
    Returns:
        最佳匹配的 CNKIPaper 对象，未找到返回 None
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None
    
    try:
        pool = get_browser_pool()
        page = pool.navigate_to_cnki()
        
        # 输入搜索关键词
        page.fill("#txt_SearchText", query, timeout=15000)
        time.sleep(random.uniform(0.1, 0.3))
        
        # 点击搜索
        page.click(".search-btn", timeout=15000)
        time.sleep(random.uniform(2, 3))
        
        # 获取结果
        result_titles = []
        result_urls = []
        try:
            results = page.query_selector_all('#gridTable a.fz14')
            for r in results:
                result_titles.append(r.inner_text().strip())
                result_urls.append(r.get_attribute("href"))
        except:
            pass
        
        if not result_titles:
            return None
        
        idx = find_closest_title(query, result_titles)
        best_url = result_urls[idx]
        
        # 获取详情
        return get_paper_detail(best_url)
    
    except Exception as e:
        logger.error(f"查找最佳匹配失败: {e}")
        return None


# =================== 文献池构建器（兼容原接口）===================

class CNKIPoolBuilder:
    """
    CNKI 文献池构建器
    
    与原有的基于 MCP 的 CNKIPoolBuilder 兼容的接口
    """
    
    def __init__(
        self,
        keywords: List[str],
        max_results: int = 10,
        min_citations: int = 0,
        year_range: Optional[tuple] = None,
        search_type: str = "主题",
        sort: str = "被引"
    ):
        """
        初始化文献池构建器
        
        Args:
            keywords: 搜索关键词列表
            max_results: 每个关键词最大结果数
            min_citations: 最小被引次数过滤
            year_range: 年份范围元组 (start, end)
            search_type: 搜索类型
            sort: 排序方式
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise BrowserError("Playwright 未安装。请运行: pip install playwright && playwright install chromium")
        
        self.keywords = keywords
        self.max_results = max_results
        self.min_citations = min_citations
        self.year_range = year_range
        self.search_type = search_type
        self.sort = sort
        self.papers: List[CNKIPaper] = []
    
    def build(self) -> List[CNKIPaper]:
        """
        构建文献池
        
        Returns:
            过滤后的论文列表
        """
        all_papers: dict = {}
        
        for keyword in self.keywords:
            logger.info(f"搜索 CNKI: {keyword}")
            
            try:
                result = search_cnki(
                    query=keyword,
                    search_type=self.search_type,
                    pages=1,
                    sort=self.sort
                )
                
                if result.get("isError"):
                    logger.warning(f"搜索失败: {result.get('error')}")
                    continue
                
                papers_data = result.get("papers", [])
                
                for paper_data in papers_data[:self.max_results]:
                    if paper_data.get("url") and paper_data["url"] not in all_papers:
                        # 获取详情
                        try:
                            detail = get_paper_detail(paper_data["url"])
                            if detail.title:  # 确保获取成功
                                all_papers[paper_data["url"]] = detail
                            else:
                                all_papers[paper_data["url"]] = CNKIPaper.from_search_result(paper_data)
                        except Exception as e:
                            logger.warning(f"获取详情失败: {e}")
                            all_papers[paper_data["url"]] = CNKIPaper.from_search_result(paper_data)
                
                # 避免请求过快
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"搜索关键词 '{keyword}' 失败: {e}")
                continue
        
        # 过滤
        filtered = self._filter_papers(list(all_papers.values()))
        self.papers = filtered
        
        logger.info(f"CNKI 文献池构建完成: {len(filtered)} 篇")
        return filtered
    
    def _filter_papers(self, papers: List[CNKIPaper]) -> List[CNKIPaper]:
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
        
        logger.info(f"CNKI 文献池已保存: {output_path}")
    
    def generate_references(self, style: str = "gb7714") -> List[str]:
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
        year = paper.year or (paper.date[:4] if paper.date else "")
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


# =================== 模块测试入口 ===================

def main_test():
    """模块测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试CNKI爬虫模块")
    parser.add_argument(
        "--query",
        type=str,
        default="计算机",
        help="测试搜索关键词（默认: 计算机）"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="爬取页数（默认: 1）"
    )
    parser.add_argument(
        "--sort",
        type=str,
        default="被引",
        choices=["相关度", "发表时间", "被引", "下载"],
        help="排序方式（默认: 被引）"
    )
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    # 测试搜索
    print("=" * 50)
    print("测试 CNKI 搜索 (Playwright 版本)")
    print("=" * 50)
    print(f"搜索关键词: {args.query}")
    print(f"页数: {args.pages}, 排序: {args.sort}")
    print("-" * 50)
    
    result = search_cnki(query=args.query, pages=args.pages, sort=args.sort)
    
    if result.get("isError"):
        print(f"错误: {result.get('error')}")
    else:
        print(f"找到 {result['total_papers']} 篇论文:")
        for i, paper in enumerate(result['papers'][:5], 1):
            print(f"\n[{i}] {paper['title']}")
            print(f"    作者: {', '.join(paper['authors'])}")
            print(f"    来源: {paper['source']}")
            print(f"    被引: {paper['cited_count']}")
    
    # 关闭浏览器
    close_browser_pool()


if __name__ == "__main__":
    main_test()
