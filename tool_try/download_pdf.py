import os
import re


from playwright.sync_api import sync_playwright

def export_webpage_to_pdf(url: str, output_path: str):
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
        output_path = os.path.join(output_path, f"{clean_title}.pdf")

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


# 测试一下
if __name__ == "__main__":
    target_url = "https://hello-agents.datawhale.cc/#/"
    target_url2 = "https://baike.baidu.com/item/%E9%BB%91%E7%A5%9E%E8%AF%9D%EF%BC%9A%E6%82%9F%E7%A9%BA/53303078"
    export_webpage_to_pdf(target_url, "../download_pdf")
    export_webpage_to_pdf(target_url2, "../download_pdf")
