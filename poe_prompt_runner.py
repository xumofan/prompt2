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
    """Return non-empty values from the first column of a CSV or Excel file."""
    if table_path.suffix.lower() in {".xlsx", ".xls"}:
        frame = pd.read_excel(table_path, engine="openpyxl")
    else:
        frame = pd.read_csv(table_path)
    if frame.shape[1] == 0:
        raise ValueError("Input table has no columns.")

    first_col = frame.iloc[:, 0].dropna().astype(str)
    values = [value.strip() for value in first_col if value.strip()]
    if not values:
        raise ValueError("No data found in the first column.")
    return values


def load_prompts(prompt_file: Path) -> List[str]:
    """Load prompts from a text file (one prompt per non-empty line)."""
    text = prompt_file.read_text(encoding="utf-8")
    prompts = [line.strip() for line in text.splitlines() if line.strip()]
    if not prompts:
        raise ValueError("No prompts found in prompt file.")
    return prompts


def build_client() -> openai.OpenAI:
    # load_dotenv(".\.env", override=True)
    # dotenv_path = find_dotenv()
    # import pdb; pdb.set_trace()
    # api_key = os.getenv("POE_API_KEY")
    # if not api_key:
    #     raise RuntimeError("POE_API_KEY is missing. Add it to your .env file.")
    return openai.OpenAI(api_key=POE_API_KEY, base_url="https://api.poe.com/v1")


def run_prompt(client: openai.OpenAI, model: str, prompt: str, item: str) -> str:
    content = f"{prompt}\n\nCount value: {item}"
    chat = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
    )
    return chat.choices[0].message.content


def export_result(output_dir: Path, prompt_idx: int, item_idx: int, payload: dict) -> Path:
    filename = f"result_prompt{prompt_idx + 1}_item{item_idx + 1}.json"
    path = output_dir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
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

    table_path = Path(args.table).expanduser().resolve()
    prompt_path = Path(args.prompts).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    items = extract_first_column(table_path)
    if args.limit is not None:
        items = items[: args.limit]
    prompts = load_prompts(prompt_path)
    client = build_client()

    summary = []
    for item_idx, item in enumerate(items):
        for prompt_idx, prompt in enumerate(prompts):
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

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(summary)} results. Summary: {summary_path}")


if __name__ == "__main__":
    main()
