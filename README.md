# Poe Prompt Runner

本项目提供一个脚本，用于：
- 从表格（CSV / Excel）读取第一列的条目
- 批量运行预设提示词到 Poe API
- 将结果以 JSON 形式输出到 `outputs/`

## 准备工作

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建 `api_key.py`

Poe API 需要通过 `POE_API_KEY` 进行认证。脚本默认从 `api_key.py` 中读取该变量。

在项目根目录创建一个名为 `api_key.py` 的文件，内容示例：

```python
# api_key.py
POE_API_KEY = "在这里替换成你的 Poe API Key"
```

注意事项：
- 请使用双引号或单引号包裹字符串；
- 不要在 key 两侧添加多余的空格或换行；
- 建议将 `api_key.py` 加入 `.gitignore`，避免密钥泄露（仓库已默认忽略）。

## 运行

```bash
python poe_prompt_runner.py --table test_cases.xlsx --prompts image_prompt.txt --output outputs --model claude-haiku-4.5
```

- `--table`：CSV/Excel 文件路径，脚本会提取第一列的非空值；
- `--prompts`：包含提示词的文本文件路径，每行一个提示；
- `--output`：结果保存目录，默认 `outputs/`；
- `--model`：Poe 模型名称，默认 `claude-haiku-4.5`；
- `--limit`：可选，限制处理的表格行数。

执行结束后，`outputs/` 目录下会生成若干 `result_prompt*_item*.json` 文件以及一个 `summary.json` 汇总。

## 其他说明

- 如果更倾向于从 `.env` 读取 key，也可以在 `poe_prompt_runner.py` 中启用相关注释，改为 `load_dotenv()` + `os.getenv("POE_API_KEY")` 的方式。
- 当前流程优先 `api_key.py`，是为了避免运行环境中缺失环境变量导致的报错。
