# 需求分析助手（Requirement Analysis Assistant）

基于 OpenCode 本地会话的需求分析质量门禁与测试用例生成 Web 服务。

不调用远程模型 API，由服务器上的 OpenCode Server 会话执行项目本地命令与约束。模型负责生成和修复内容，本地 Python 程序负责质量判定与正式结果生成，质量判定以本地校验程序为准。

## 功能特性

- 上传需求文档（Markdown / TXT / DOCX / PDF），自动执行「需求分析 → 质量门禁 → 测试用例生成 → 校验」全流程
- 任务状态跟踪：`queued / analyzing / generating / completed / human_required / failed`
- 完成后提供 4 个下载产物：`需求分析结果.md`、`validated/analysis.json`、`test_cases.md`、`test_cases.json`
- 登录保护与账号设置（默认账号见下文，请及时修改）
- 测试用例由人工执行，系统不自动执行

## 架构

```
浏览器 → Flask Web (0.0.0.0:8080) → opencode serve (127.0.0.1:4096) → 项目目录 OpenCode 会话
```

- Web 服务：Flask（`requirements.txt` 仅需 `Flask>=3.0,<4`）
- 执行器：OpenCode Server 本地会话（版本 1.18.18+，模型 `deepseek-v4-flash`）
- OpenCode 服务仅监听 `127.0.0.1`，不暴露到公网

## 快速开始

### 1. 启动 OpenCode Server

在项目根目录运行：

```bash
opencode serve --hostname 127.0.0.1 --port 4096
```

### 2. 安装依赖并启动 Web 服务

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

浏览器访问 `http://127.0.0.1:8080`。

首次运行自动创建默认账号 `admin / admin123`，请立即通过页面右上角「账号设置」或命令行修改：

```bash
python app.py set-password
```

### 3. 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `WEB_HOST` | `127.0.0.1` | Web 服务监听地址 |
| `WEB_PORT` | `8080` | Web 服务端口 |
| `OPENCODE_URL` | `http://127.0.0.1:4096` | OpenCode Server 地址 |

## 使用流程

1. 上传需求文档，任务自动开始（后台串行执行两个命令，页面只显示状态，不展示中间过程）
2. 等待任务完成或进入人工介入状态
3. 完成后下载 4 个产物：
   - `需求分析结果.md`：人类可读的需求分析测试点清单
   - `validated/analysis.json`：通过质量门禁的机器可读结果
   - `test_cases.md`：人类可读的测试用例
   - `test_cases.json`：测试用例权威数据源

## 固定流程与约束

项目的协作流程定义在 `AGENTS.md` 中，不可违反：

1. 读取需求文档与冻结的 `prompt.md`，生成 `analysis.json`
2. 执行质量门禁 `python -m analysis_quality_gate.pipeline process analysis.json --output-dir output`
3. 读取 `output/reports/validation.json`，失败则修复 `analysis.json`（禁止修改 `prompt.md`），最多修 2 次
4. 通过后产出 `output/需求分析结果.md` 与 `output/validated/analysis.json`
5. 测试用例生成与校验：`python test_case_generation\validate_test_cases.py output\validated\analysis.json test_case_generation\test_cases.json`
6. 质量判定以本地校验程序为准，不以模型自检结论为准

## 目录结构

```
app.py                                # Flask Web 服务入口
AGENTS.md                             # 固定协作流程（不可违反）
prompt.md                             # 冻结的需求分析提示词
analysis_quality_gate/                # 结构校验、业务校验、Markdown 渲染
test_case_generation/                 # 测试用例生成提示词、校验与渲染
.opencode/commands/                   # OpenCode 会话命令
web/                                  # 前端页面与静态资源
requirements.txt                      # 依赖清单
WEB_README.md                         # Web 部署与运维说明
```

## 说明与注意事项

- `output/`、`analysis.json`、`test_cases.json` 等均为运行时生成产物，不入版本库
- 上传的需求文档保存为项目根目录 `需求文档-{任务ID}.后缀`
- 当前 MVP 使用项目目录中的共享输出文件，适合单任务/单用户验证；多用户并发需将任务隔离到独立工作区
- 生产部署建议配合 HTTPS（Nginx）与 UFW 限制，OpenCode Server 不直接暴露公网
- 详细部署（systemd、Nginx、环境变量）见 [WEB_README.md](WEB_README.md)
