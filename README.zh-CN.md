# Q-One Agent

[![CI](https://github.com/aidless/q-one-agent/actions/workflows/checks.yml/badge.svg)](https://github.com/aidless/q-one-agent/actions/workflows/checks.yml)

**English documentation: [README.md](README.md)**

**限制：** 本仓库没有保存任何真实 provider 的调用结果。云端传输只做了 fixture 测试，没有做过线上验证。没有保存下来的连通性回执。不声称精度、用户数或采用数。STATUS: WORK-IN-PROGRESS — not A yet.

## 问题

Q-One Agent 把一条结构化决策路由给一个 provider，并产出一条可供 q-one-core 记录的推荐。
它不写入人的决定，也从不把推荐标成可以自动执行。
`qone-agent` CLI 默认是确定性的 `cost-heuristic-v0.1`；`run_model` 调用 Ollama、Laya 或已配置的云端端点，并在离线故障矩阵的那些故障上抛出异常，而不是用该演示启发式顶替。

## 连通性回执

`RunResult.receipt()` 只在 `run_model` 成功返回推荐之后，在内存里组成一份字典。字段是 `run_id`、`provider`、`model`、`duration_ms`、`input_sha256`、`usage`、`evidence_ids`。其中没有推荐正文。

本仓库没有保存任何回执。本仓库没有记录任何一次已经发出的请求：没有一次完成调用的时间戳，也没有一份作答的模型 revision。代码里的默认 Ollama 地址是 `http://127.0.0.1:11434`。代码里的默认名字是 `qwen3:8b`。代码里的 Laya checkpoint 字符串是 `convaiinnovations/laya-multilingual`，revision 为 `1720e3e3357cfe1e281542e223f8273b0890ca34`。这些是配置默认值，不是某个进程作答的证据。

矩阵里的 HTTP 故障使用 `httpx.MockTransport` 或一个已关闭的本机回环端口。云端传输没有做过线上验证。

## 安全矩阵

`make check` 会离线重算 `eval/fault-matrix.json`，并在提交的文件与重算结果不一致时失败。矩阵是三个适配器（Ollama、Laya、云端）乘五类故障（连接被拒绝、超时、畸形 JSON、不符合 schema 的输出、空内容）。十四格抛出 `ProviderError`。Laya 的连接被拒绝一格抛出 `ConnectionRefusedError`，因为该适配器没有 HTTP 客户端。没有任何一格返回 `cost-heuristic-v0.1`。另一组 fixture 表明，模型 JSON 里即使写了 `auto_eligible: true`，返回值仍是 `auto_eligible: false` 且 `requires_human: true`。

细节和残留限制见 [FAILURE_MODES.md](FAILURE_MODES.md)。

## Schema 钉扎

推荐校验使用从 [q-one-core](https://github.com/aidless/q-one-core) 提交 `2d243b33c0beede7cf05d1ab2212f5fb45d39c6a` 摘来的校验函数（`schemas/vendor/q-one-core/`）。该提交的 q-one-core 没有发布推荐的 JSON Schema 文件。CLI 引擎的输出同时通过该校验函数和本仓的 `schemas/recommendation.schema.json`。`run_model` 的输出通过该校验函数，但被本地 schema 拒绝，因为它缺少 `decision_id` 和 `gate_reasons`。本仓不调用 core 的 `DecisionService`。

`examples/agent_input.json` 的决策 id 是 `D-20261023-example`，不符合 core 决策 id 的模式 `^D-[0-9]{8}-[a-f0-9]{6}$`。

## 三个仓库

- [`q-one-core`](https://github.com/aidless/q-one-core) 拥有决策与事件协议。其诚实边界拉取请求 [q-one-core#1](https://github.com/aidless/q-one-core/pull/1) 在 2026-11-16 仍打开且未合并。
- `q-one-agent` 拥有路由、provider 适配器、证据捕获与推荐格式化。
- [`q-one-life`](https://github.com/aidless/q-one-life) 拥有个人应用。其诚实边界拉取请求 [q-one-life#1](https://github.com/aidless/q-one-life/pull/1) 在 2026-11-16 仍打开且未合并。

## 快速开始

需要 Python 3.10 或更新版本。安装依赖只有 `httpx`。安装之后，`make check` 不需要网络。在 Debian 和 Ubuntu 上，`python3 -m venv` 需要发行版软件包 `python3-venv` 之后，下面的命令才能用。GitHub Actions 的 `setup-python` 镜像里已经带了它。

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
qone-agent providers
qone-agent recommend --decision-file examples/agent_input.json
make check
```

2026-11-16 在本变更所用机器上观察（Python 3.12.3，新建 venv，`pip install -e .`）。这是确定性 CLI 演示，不是模型调用：

```text
$ qone-agent providers
cost-heuristic-v0.1
```

`qone-agent recommend --decision-file examples/agent_input.json` 打印的推荐中，`option_id` 为 `meeting`，`source` 为 `cost-heuristic-v0.1`，`requires_human` 为 true，`auto_eligible` 为 false，`success_probability` 为 null。完整 JSON 以重新运行该命令为准。同一形状写在 `eval/fault-matrix.json` 的 `cli_heuristic_demo` 里。

## 不证明什么

[PREREG.md](PREREG.md) 里的计划比较 C1–C3 没有跑过。[docs/MODEL_RESEARCH.md](docs/MODEL_RESEARCH.md) 没有真实调用记录。没有精度、校准、用户数或采用数。Laya 权重和 PyTorch 不在基础安装里（`pip install '.[laya]'` 只声明可选依赖）。

`python3 eval/run_cases.py` 重算可执行验收题。`python3 eval/run_cases.py --selftest` 必须变红。

## GitHub About

这次提交不修改 GitHub About 字段。2026-11-16 该字段是："Provider-neutral orchestration for the Q-One decision protocol"。它没有写明上面的限制。

About replacement: Routes one structured decision to a provider and returns a human-reviewed recommendation for q-one-core. It does not write the human decision or mark a recommendation safe for automatic execution. The CLI demo is cost-heuristic-v0.1. No live-provider result is stored in this repository.

本项目以 MIT 许可发布。失败模式：[FAILURE_MODES.md](FAILURE_MODES.md)。
