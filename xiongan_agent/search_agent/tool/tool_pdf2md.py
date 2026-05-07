# Copyright (c) Opendatalab. All rights reserved.
import asyncio
import os
import tempfile
from pathlib import Path

import httpx
from langchain_core.tools import tool

from mineru.cli import api_client as _api_client
from mineru.cli.common import image_suffixes, office_suffixes, pdf_suffixes
from mineru.utils.guess_suffix_or_lang import guess_suffix_by_path

SUPPORTED_INPUT_SUFFIXES = set(pdf_suffixes + image_suffixes + office_suffixes)


def collect_input_files(input_path: str | Path) -> list[Path]:
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        file_suffix = guess_suffix_by_path(path)
        if file_suffix not in SUPPORTED_INPUT_SUFFIXES:
            raise ValueError(f"Unsupported input file type: {path.name}")
        return [path]

    if not path.is_dir():
        raise ValueError(f"Input path must be a file or directory: {path}")

    input_files = sorted(
        (
            candidate.resolve()
            for candidate in path.iterdir()
            if candidate.is_file()
               and guess_suffix_by_path(candidate) in SUPPORTED_INPUT_SUFFIXES
        ),
        key=lambda item: item.name,
    )
    if not input_files:
        raise ValueError(f"No supported files found in directory: {path}")
    return input_files


def build_form_data(
        language: str,
        backend: str,
        parse_method: str,
        formula_enable: bool,
        table_enable: bool,
        server_url: str | None,
        start_page_id: int,
        end_page_id: int | None,
) -> dict[str, str | list[str]]:
    return _api_client.build_parse_request_form_data(
        lang_list=[language],
        backend=backend,
        parse_method=parse_method,
        formula_enable=formula_enable,
        table_enable=table_enable,
        server_url=server_url,
        start_page_id=start_page_id,
        end_page_id=end_page_id,
        return_md=True,
        return_middle_json=False,
        return_model_output=False,
        return_content_list=False,
        return_images=True,
        response_format_zip=True,
        return_original_file=False,
    )


def format_status_message(status_snapshot: _api_client.TaskStatusSnapshot) -> str:
    if status_snapshot.queued_ahead is None:
        return status_snapshot.status
    return f"{status_snapshot.status} (queued_ahead={status_snapshot.queued_ahead})"


def prepare_local_api_temp_dir() -> None:
    current_temp_dir = Path(tempfile.gettempdir())
    if os.name == "nt" or not Path("/tmp").exists():
        return
    if not str(current_temp_dir).startswith("/mnt/"):
        return

    # vLLM/ZeroMQ IPC sockets fail on drvfs-backed temp directories under WSL.
    os.environ["TMPDIR"] = "/tmp"
    tempfile.tempdir = None


async def run_demo(
        input_path: str | Path,
        output_dir: str | Path,
        *,
        api_url: str | None = None,
        backend: str = "hybrid-auto-engine",
        parse_method: str = "auto",
        language: str = "ch",
        formula_enable: bool = True,
        table_enable: bool = True,
        server_url: str | None = None,
        start_page_id: int = 0,
        end_page_id: int | None = None,
) -> None:
    api_url = api_url or None
    server_url = server_url or None
    if backend.endswith("http-client") and not server_url:
        raise ValueError(f"backend={backend} requires server_url")

    input_files = collect_input_files(input_path)
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    form_data = build_form_data(
        language=language,
        backend=backend,
        parse_method=parse_method,
        formula_enable=formula_enable,
        table_enable=table_enable,
        server_url=server_url,
        start_page_id=start_page_id,
        end_page_id=end_page_id,
    )
    upload_assets = [
        _api_client.UploadAsset(path=file_path, upload_name=file_path.name)
        for file_path in input_files
    ]

    local_server: _api_client.LocalAPIServer | None = None
    result_zip_path: Path | None = None
    task_label = f"{len(input_files)} file(s)"

    async with httpx.AsyncClient(
            timeout=_api_client.build_http_timeout(),
            follow_redirects=True,
    ) as http_client:
        try:
            if api_url is None:
                prepare_local_api_temp_dir()
                local_server = _api_client.LocalAPIServer()
                base_url = local_server.start()
                print(f"Started local mineru-api: {base_url}")
                server_health = await _api_client.wait_for_local_api_ready(
                    http_client,
                    local_server,
                )
            else:
                server_health = await _api_client.fetch_server_health(
                    http_client,
                    _api_client.normalize_base_url(api_url),
                )

            print(f"Using API: {server_health.base_url}")
            print(f"Submitting {len(upload_assets)} file(s)")
            submit_response = await _api_client.submit_parse_task(
                base_url=server_health.base_url,
                upload_assets=upload_assets,
                form_data=form_data,
            )
            print(f"task_id: {submit_response.task_id}")
            if submit_response.queued_ahead is not None:
                print(f"status: pending (queued_ahead={submit_response.queued_ahead})")

            last_status_message = None

            def on_status_update(status_snapshot: _api_client.TaskStatusSnapshot) -> None:
                nonlocal last_status_message
                message = format_status_message(status_snapshot)
                if message == last_status_message:
                    return
                last_status_message = message
                print(f"status: {message}")

            await _api_client.wait_for_task_result(
                client=http_client,
                submit_response=submit_response,
                task_label=task_label,
                status_snapshot_callback=on_status_update,
            )
            print("status: completed")
            result_zip_path = await _api_client.download_result_zip(
                client=http_client,
                submit_response=submit_response,
                task_label=task_label,
            )
        finally:
            if local_server is not None:
                local_server.stop()

    assert result_zip_path is not None
    try:
        _api_client.safe_extract_zip(result_zip_path, output_path)
    finally:
        result_zip_path.unlink(missing_ok=True)
    print(f"Extracted result to: {output_path}")


@tool
def pdf2md(input_path):
    """
        将指定的本地 PDF 文件解析并返回其 Markdown 文本内容。

        支持提取文字、复杂的 LaTeX 公式和表格。
        当需要深入分析某个特定的 PDF 文档（如论文、报告）时，请调用此工具。

        参数:
            path (str): 待解析的 PDF 文件路径（例如 "download_pdf/test.pdf"）。

        返回:
            str: 解析后的 Markdown 文本。如果解析失败，返回错误描述。
    """

    # Set this to an existing MinerU FastAPI base URL, for example:
    # "http://127.0.0.1:8000"
    # Leave it as None to start a temporary local mineru-api automatically.
    api_url = None

    # Available examples:
    # "hybrid-auto-engine"   -> local hybrid parsing, recommended default
    # "pipeline"             -> more general OCR/text pipeline
    # "vlm-auto-engine"      -> local VLM parsing
    # "vlm-http-client"      -> remote OpenAI-compatible VLM server
    # "hybrid-http-client"   -> remote OpenAI-compatible hybrid server
    backend = "vlm-auto-engine"
    # Available options:
    # "auto" -> let MinerU choose between text extraction and OCR
    # "txt"  -> force text extraction
    # "ocr"  -> force OCR
    parse_method = "auto"
    # OCR language hint. This is mainly used by pipeline and hybrid backends.
    language = "ch"
    # Enable formula parsing in the output.
    formula_enable = True
    # Enable table parsing in the output.
    table_enable = True
    # Required only for "*-http-client" backends, for example:
    # "http://127.0.0.1:30000"
    server_url = None
    # Zero-based page range. Set end_page_id to None to parse to the last page.
    start_page_id = 0
    end_page_id = None

    """如果您由于网络问题无法下载模型，可以设置环境变量MINERU_MODEL_SOURCE为modelscope使用免代理仓库下载模型"""
    os.environ['MINERU_MODEL_SOURCE'] = "modelscope"
    # 1. 基础校验：确保输入是单个文件
    input_path = Path(input_path)
    if not input_path.is_file():
        return f"❌ 错误：路径 {input_path} 不是一个有效的 PDF 文件。本工具当前设定为单文件解析模式。"

    print(f"🚀 [MinerU] 正在解析单个文档: {input_path.name}")
    output_dir = Path("/home/charles/mycode/multiagent/xiongan_agent/search_agent/search_result/pdf2md")
    try:
        # 2. 调用 MinerU 执行解析
        asyncio.run(
            run_demo(
                input_path=input_path,
                output_dir=output_dir,
                backend="vlm-auto-engine",  # 使用 VLM 引擎保证公式和表格质量
                language="ch",
                formula_enable=True,
                table_enable=True,
                # 其他配置保持默认...
            )
        )

        # 3. 定向读取该文件的解析结果
        # MinerU 解析 my_doc.pdf 后，通常会生成路径：output_dir/my_doc/vlm/my_doc.md
        # 我们根据文件名（stem）精准查找
        file_stem = input_path.stem
        search_pattern = f"**/{file_stem}.md"
        md_files = list(output_dir.glob(search_pattern))

        if md_files:
            # 即使有多份历史记录，我们也只取最新生成的这一份
            latest_md = max(md_files, key=os.path.getmtime)
            with open(latest_md, 'r', encoding='utf-8') as f:
                content = f.read()

            print(f"✅ 解析成功：{file_stem}.pdf")
            content = content.encode('utf-8', 'ignore').decode('utf-8')  # 过滤非法字节

            return content
        else:
            return f"⚠️ 文件 {file_stem}.pdf 解析已完成，但未能在输出目录找到生成的 Markdown 文件。"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ 解析 PDF 时发生错误: {str(e)}"


if __name__ == "__main__":
    # path1 = Path("/home/charles/mycode/multiagent/pdf2md_output/heishihua/vlm/heishihua.md")
    path1 = "/home/charles/mycode/multiagent/download_pdf/黑神话：悟空（杭州游科互动科技有限公司开发的西游题材单机动作角色扮演游戏）_百度百科.pdf"
    a = pdf2md.invoke(path1)
    print(a)
