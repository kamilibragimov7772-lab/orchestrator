# Orchestrator — 一个可验证的 Claude Code 编排栈

**[English](README.en.md) · [Русский](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [Türkçe](README.tr.md)**

把一个 Claude Code 会话变成编排器：需求简报转成波次计划，每个波次调度专门的子代理，
每个波次都落成文件，最后由一个独立的审查者决定验收还是驳回。
包含 41 张代理卡、10 份共享契约、10 个斜杠命令、4 个可选技能。

MIT 许可。作者：**[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**。协议版本 **2.16.0**。

> **请先读这段 — 关于语言。** 编排协议、代理卡和验收标准是**用俄语写的**。
> 工具链、测试、安装流程和代码注释是英语。如果你想要的是代理本身，你将阅读俄语
> Markdown。如果你想要的是让一个代理栈变得可信的那层管道，那部分与语言无关，
> 也正是这个仓库存在的理由。

---

## 为什么会有这个项目

Claude Code 的子代理集合并不稀缺，稀缺的是**可以验证**的那种。大多数集合就是一堆
Markdown 文件：没有任何东西能证明钩子真的触发了，没有任何东西能证明密钥扫描器读的是
正确的字节，也没有任何东西会在某项检查悄悄停止工作时报错。

这个仓库选择了相反的取舍。代理库本身很普通，**重点是它周围的管道**：

| 大多数集合提供的 | 这里提供的 |
|---|---|
| 只有代理 Markdown | 代理**外加**守卫、安装器、体检、验收关卡、同步 |
| 没有测试 | **97 个测试**，仅用标准库，不调用 API，不联网 |
| 「把这段加进 settings.json」 | 带冲突预检的安装器；**体检会真的运行守卫**并要求它拦截 |
| 假定钩子能工作 | 三负载冒烟测试：正常必须通过，密钥必须拦截，危险命令必须拦截 |
| 「很安全，相信提示词」 | 提示词文本从不被当作访问边界 — 见 [SECURITY.md](SECURITY.md) |

凡是脚本能检查的，都交给脚本检查。因为只活在提示词里的规则，就是会悄悄失效的规则。

---

## 快速开始

需要 **Python 3.10+** 和 **Git**。不需要 API 密钥，不联网，不调用模型：

```sh
git clone https://github.com/kamilibragimov7772-lab/orchestrator
cd orchestrator
python tools/verify.py
```

这会运行代理契约检查器、就绪计数器自检、完整测试套件和一次密钥扫描，
不会碰检出目录以外的任何东西。

安装到你自己指定的目录 — 安装器**先给计划，绝不覆盖**：

```sh
python tools/install.py \
  --destination /absolute/path/stack \
  --vault /absolute/path/knowledge-base \
  --mode minimal
```

看过计划后，加上 `--apply` 再运行一次。如果某个目标文件已存在且内容不同，
安装会停止并保留你的文件。然后确认结果：

```sh
python tools/doctor.py --root /absolute/path/stack --installed
```

`minimal` 安装七个角色，面向调研和 Markdown 交付物。`full` 追加软件 / 建站 / 媒体
流水线及其外部依赖。Windows 说明和如何让 Claude Code 指向新目录：[INSTALL.md](INSTALL.md)。

---

## 里面有什么

| 层 | 用途 | 验证边界 |
|---|---|---|
| `_orchestr_protocol.md`、`agents/`、`commands/` | 路由、契约、完成定义 | 检查器只验结构；回答质量仍需人工验收 |
| `tools/verify.py`、`tests/` | 一条可复现的命令，含反面用例 | 不用 Claude API，不用外部 MCP |
| `tools/guard.py` | PreToolUse 阶段识别凭据与破坏性命令 | **启发式纵深防御** — 请保留宿主权限与沙箱 |
| `tools/install.py`、`tools/doctor.py` | 非破坏性安装；就绪报告 | 体检不测试鉴权，也不测试模型质量 |
| `tools/acceptance-gate/` | 确定性的运行日志检查 + 可选审查工作进程 | 模型工作进程**默认关闭**；未认证端到端 |
| `tools/sync_stack.py` | 基于精确白名单的 Git 桥 | 可选；不会替你合并已分叉的分支 |
| `tools/export_session.py` | 选择性开启的会话导出 | **默认关闭**；脱敏基于模式匹配，不是隐私保证 |

### 验收关卡

最花时间才做对的一件事。一次运行结束后，由一个**独立上下文**（它从未看过编排器的推理过程）
对照需求简报评判交付物。确定性脚本先跑，模型只评判脚本判不了的部分：

- `run_status` 与 `verdict` 是两个字段。状态不是 `done` 的运行返回
  *「不适用验收」*，而不是伪造的通过。
- `SKIP` 得出**「不完整」**，绝不会变成「通过」。PDF 被报告为*仅校验了签名 —
  请在阅读器里打开*；`.docx` 报告为*结构可解析，视觉验收另计*。
- 退出码彼此区分：`0` 通过 · `1` 驳回 · `3` 不完整 · `4` 不适用 · `2` 错误。

依据是作者在 259 次运行上的实测：进了校验器的规则，遵守率 76–100%；
同一条规则只写在提示词里，遵守率 0–39%。

---

## 它刻意不做的事

信任在很大程度上，是一份「它不会背着你做什么」的清单：

- **安装时不会自动开启导出、镜像、Git 推送、定时任务或模型进程。** 每一项都需要
  显式配置才会启用。
- **没有 `robocopy /MIR` 式的镜像。** 那会删除目标端存在而源端没有的文件，已被移除。
- **不覆盖。** 冲突文件会中止安装；你的设置和钩子是被合并，不是被替换。
- **不会静默通过。** 缺失的依赖或未执行的检查会报告 `NOT CHECKED` 或 `SKIP`，
  绝不谎报一个没挣来的通过。
- **不宣称未经证明的评分。** 曾以「9.5/10」为目标且**未获认证** — 未决项列在
  [`audit_9_5/`](audit_9_5/) 里，而不是被平均值抹平。

---

## 验证状态

CI 覆盖 Windows / Linux / macOS × Python 3.10 与 3.12，解析每个 PowerShell 脚本，
并用 Gitleaks 扫描**整个 Git 历史**。见 [`.github/workflows/ci.yml`](.github/workflows/ci.yml)。

诚实的边界，因为一个绿色徽章不等于证据：

- 测试覆盖工具行为，不覆盖代理写出内容的质量。
- 真实模型的端到端验收**不在**套件覆盖范围内。
- 守卫是启发式的。它们补充宿主权限，而不是取代宿主权限。

---

## 文档

| 文件 | 回答什么 |
|---|---|
| [INSTALL.md](INSTALL.md) | 安装、接入 Claude Code、Windows 细节 |
| [AGENTS.md](AGENTS.md) | 参与本代码库开发的入口 |
| [SECURITY.md](SECURITY.md) | 守卫保护什么、不保护什么；导出隐私 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 一次改动必须通过的检查 |
| [CHANGELOG.md](CHANGELOG.md) | 行为变更 |

## 方法论依据

工程基线：**NIST SSDF 1.1**（NIST，2022）— 复现缺陷、修复、补一条能拒绝该缺陷的回归测试 —
并结合宿主官方文档（[Claude Code hooks](https://code.claude.com/docs/en/hooks)）。
核对日期 2026-09-06。SSDF 用于筛选风险，不作为合规证书。

## 许可

[MIT](LICENSE)。作者 **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**。
