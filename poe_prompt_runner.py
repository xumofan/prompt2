"""批量读取表格第一列，依次调用 Poe 模型执行提示词，并把结果保存到 JSON 文件。"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

import openai
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from api_key import POE_API_KEY


def extract_first_column(table_path: Path) -> List[str]:
    """从 CSV 或 Excel 文件中提取第一列的所有非空值。"""
    # 根据文件后缀选择读取方式，确保 CSV/Excel 两种格式都能兼容。
    if table_path.suffix.lower() in {".xlsx", ".xls"}:
        frame = pd.read_excel(table_path, engine="openpyxl")
    else:
        frame = pd.read_csv(table_path)
    # 如果表格一列都没有，提前抛错，提醒用户修复输入文件。
    if frame.shape[1] == 0:
        raise ValueError("Input table has no columns.")

    # 仅保留第一列，去掉 NA，统一转成字符串并裁剪空白字符。
    first_col = frame.iloc[:, 0].dropna().astype(str)
    values = [value.strip() for value in first_col if value.strip()]
    if not values:
        raise ValueError("No data found in the first column.")
    return values


def load_prompts(prompt_file: Path) -> List[str]:
    text = prompt_file.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("No prompts found in prompt file.")
    return [text]

def build_client() -> openai.OpenAI:
    """创建配置好的 OpenAI 客户端，指向 Poe 的 API 入口。"""
    # 如果希望改为从 .env 读取，可以取消下面的注释：
    # load_dotenv(find_dotenv(), override=True)
    # api_key = os.getenv("POE_API_KEY")
    # if not api_key:
    #     raise RuntimeError("POE_API_KEY is missing. Add it to your .env file.")

    # 当前版本直接从 api_key.py 读取密钥，避免运行时查找环境变量失败。
    return openai.OpenAI(api_key=POE_API_KEY, base_url="https://api.poe.com/v1")


def run_prompt(client: openai.OpenAI, model: str, prompt: str, item: str) -> str:
    """把一个提示词与表格值拼接后发送到 Poe 模型，并返回回复文本。"""
    # 将提示模板与当前表格项组合，保证模型能够感知到当前上下文。
    content = f"{prompt}\n\nCount value: {item}"
    chat = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
    )
    return chat.choices[0].message.content


def export_result(output_dir: Path, prompt_idx: int, item_idx: int, payload: dict) -> Path:
    """将单次请求的原始输入/输出以及元数据写入独立 JSON 文件。"""
    # 文件名包含提示索引和表格索引，方便事后追溯来源。
    filename = f"result_prompt{prompt_idx + 1}_item{item_idx + 1}.json"
    path = output_dir / filename
    # ensure_ascii=False 能保留中文或其他 Unicode 字符，indent=2 方便人工查看。
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    # 使用 argparse 暴露核心参数，方便在命令行或脚本中复用。
    parser = argparse.ArgumentParser(
        description="Extract first-column data, test prompts via Poe API, and export results."
    )
    parser.add_argument("--table", required=True, help="Path to CSV/Excel table.")
    parser.add_argument("--prompts", required=True, help="Path to prompt .txt file.")
    parser.add_argument(
        "--output",
        default="outputs",
        help="Directory to store individual JSON results and the summary file.",
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4.5",
        help="Poe model name to use.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optionally limit how many table rows to process.",
    )
    args = parser.parse_args()

    # 统一把路径转成绝对路径并确保输出目录存在，避免后续频繁判断。
    table_path = Path(args.table).expanduser().resolve()
    prompt_path = Path(args.prompts).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载表格数据与提示词集合，limit 参数可以用于抽样测试。
    items = extract_first_column(table_path)
    if args.limit is not None:
        items = items[: args.limit]
    prompts = load_prompts(prompt_path)

    # 客户端只初始化一次，后续循环中反复复用，避免重复握手。
    client = build_client()

    summary = []
    for item_idx, item in enumerate(items):
        for prompt_idx, prompt in enumerate(prompts):
            # 对每一个 (表格值, 提示词) 组合都发起一次调用，并记录所有上下文。
            response = run_prompt(client, args.model, prompt, item)
            record = {
                "prompt_index": prompt_idx + 1,
                "item_index": item_idx + 1,
                "table_value": item,
                "prompt": prompt,
                "model": args.model,
                "response": response,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            result_path = export_result(output_dir, prompt_idx, item_idx, record)
            summary.append({**record, "file": str(result_path)})

    # 汇总文件记录了每个结果文件的路径，可用于后续分析或合并。
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(summary)} results. Summary: {summary_path}")


if __name__ == "__main__":
    main()
