import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright
from langchain_core.tools import tool


@tool
def export_webpage_to_pdf(query: str, url: str):
    """
        将指定的网页完整内容导出并保存为本地 PDF 文件。

        当用户需要保存网页资料、打印文章、或者要求“下载/保存”某个网页为文件时，应调用此工具。
        该工具会模拟浏览器渲染页面，包含图片和背景，并自动根据网页标题生成文件名。

        参数:
            query(str):用户最初的提问
            url (str): 想要导出的网页完整 URL 地址。

        返回:
            str: 导出的 PDF 文件在本地的绝对路径。如果导出失败，将返回错误描述。
        """
    # 启动 playwright 引擎
    with sync_playwright() as p:
        # 启动 Chromium 浏览器（headless=True 表示无头模式，不弹出肉眼可见的窗口）
        browser = p.chromium.launch(headless=True)

        # 创建一个新页面
        page = browser.new_page()

        print(f"正在访问: {url} ...")
        # 访问网页，wait_until='networkidle' 非常关键！
        # 它意味着等待网页上所有网络请求都几乎停止了（即动态数据都加载完了）才继续
        page.goto(url, wait_until="load")
        page.emulate_media(media="screen")
        raw_title = page.title() or "untitled"

        def sanitize_filename(filename: str) -> str:
            """
            清洗文件名，移除操作系统不允许的特殊字符。
            """
            # 移除 / \ : * ? " < > | 等字符
            return re.sub(r'[\\/*?:"<>|]', "_", filename).strip()

        clean_title = sanitize_filename(raw_title)

        current_file = Path(__file__).resolve()
        base_dir = current_file.parent.parent.parent
        output_dir = base_dir / "search_result" / "download_pdf" / f"{query}"
        output_path = os.path.join(output_dir, f"{clean_title}.pdf")

        print(f"🧠 [AI] 检测到网页标题: {raw_title}")
        print(f"✍️ [SYSTEM] 正在生成 PDF: {output_path} ...")
        if os.path.exists(output_path):
            print(f"⚠️ [SKIP] 文件已存在，跳过生成: {output_path}")
            browser.close()
            return
        # 调用浏览器的打印功能导出 PDF
        page.pdf(
            path=output_path,
            format="A4",  # 纸张大小
            print_background=True,  # 打印背景颜色和图片（重要，否则可能是一片白）
            margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"},
        )

        # 关闭浏览器
        browser.close()
        print("✅ 导出完成！")
    return output_path
