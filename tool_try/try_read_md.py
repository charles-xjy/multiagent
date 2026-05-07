# 3. 核心改进：批量读取并合并所有生成的 Markdown 文件
import os
from pathlib import Path

combined_markdown = []

output_dir = Path("/home/charles/mycode/multiagent/pdf2md_output/")

# 遍历所有目标文件，在输出目录下寻找对应的 .md
search_pattern = "**/**/*.md"
md_files = list(output_dir.glob(search_pattern))

if md_files:
    # 找到该文件对应的最新解析结果
    for latest_md in md_files:
        with open(latest_md, 'r', encoding='utf-8') as f:
            content = f.read()
            # 为多个文件增加分隔符，方便 Agent 区分
            combined_markdown.append(f"{content}\n\n---\n")


