# AI 能力升级说明（2026-05）

## 1. 本次升级目标

这次升级的核心目标，不是单纯“再加几个 AI 按钮”，而是把项目升级成一个能够清晰展示以下能力的作品：

- AI 在英语学习产品中的真实落地
- Agent 工作流与决策链路
- RAG 与向量检索的结合方式
- MCP 风格工具层的设计
- AI 可观测性、缓存与证据区展示

这个方向更适合写进简历，也更适合在面试时直接演示。

## 2. 新增的关键能力

### 2.1 AI 重规划学习计划 Agent

新增接口：

- `POST /api/v1/ai/plans/replan`

能力说明：

- 读取当前学习计划
- 读取今日任务与 adaptive 建议
- 读取错词本与到期复习词
- 读取近期学习趋势
- 结合 structured RAG 与 vector RAG
- 输出新的学习顺序、建议日目标、复习目标、时间块建议和计划 patch

这个能力已经不只是“AI 给一句建议”，而是具备了明确输入、工具调用、知识检索、决策输出的 Agent 形态。

### 2.2 统一 AI 证据区

多数 AI 接口现在都会返回统一的 `evidence` 结构，包含：

- `summary`
- `workflow`
- `tools_used`
- `retrieval_hits`
- `observability`

这样前端每次展示 AI 结果时，不仅能展示答案，还能展示：

- 这次 AI 经过了哪些步骤
- 用了哪些工具
- 命中了哪些知识片段
- 是否命中缓存
- 耗时多少
- 用的是什么模型和 prompt 版本

### 2.3 AI 中心重构为能力展示页

原来的 AI 中心更像一个功能入口集合页。

现在已经重构成按能力分区的展示页，重点展示：

- Agent
- RAG
- MCP
- AI 应用场景
- 可观测性

更适合做项目演示、答辩和简历项目说明。

### 2.4 MCP 风格工具层展示

当前后端已提供：

- `GET /api/v1/ai/mcp/manifest`
- `GET /api/v1/ai/mcp/resources`
- `GET /api/v1/ai/mcp/prompts`
- `POST /api/v1/ai/mcp/tools/call`

并补充了 `plan_replanner` 工具能力。

这使项目可以明确展示“把业务能力抽象成 AI tool / resource / prompt”的工程思路，而不是只有模型调用。

### 2.5 AI 可观测性增强

通过 `run_observed_feature(...)`，多个 AI 接口现在统一记录：

- `cache_hit`
- `cache_key`
- `latency_ms`
- `endpoint`
- `status`
- `prompt_version`
- `model_name`

对应能力已经在：

- AI 结果 evidence 区
- AI 质量摘要
- AI 观测页
- `ai_run_logs`
- `ai_response_cache`

中打通。

## 3. 已落地到前端的展示点

### 3.1 AI 中心

现在 AI 中心可以直接展示：

- AI 重规划学习计划 Agent
- 结构化 RAG
- 向量 RAG
- RAG 召回评测
- MCP tools / resources / prompts
- 语法导学
- 多 Agent 协作简报
- AI 学习报告
- AI 运行观测

### 3.2 业务页面中的 evidence 区

以下页面已接入证据区展示：

- 首页 AI 学习教练
- 学习页 AI 讲词
- 单词详情页 AI 讲词
- 错词本 AI 复盘

这意味着用户在真实使用 AI 功能时，也能看到“答案为什么这样来”。

## 4. 后端新增 / 关键文件

### 新增文件

- `backend/apps/ai/evidence.py`
- `backend/apps/ai/graphs/plan_replanner.py`
- `front/components/ai-evidence/ai-evidence.*`

### 关键更新文件

- `backend/apps/ai/views.py`
- `backend/apps/ai/urls.py`
- `backend/apps/ai/serializers.py`
- `backend/apps/ai/conversation_services.py`
- `backend/apps/ai/mcp/server_http.py`
- `backend/apps/ai/observability.py`
- `front/pages/ai-center/index.*`
- `front/pages/home/index.*`
- `front/pages/learn/index.*`
- `front/pages/word-detail/index.*`
- `front/pages/wrong-words/index.*`
- `front/services/modules/ai.js`

## 5. 简历可写的项目亮点

可以往简历里提炼成下面这种表述：

1. 设计并实现英语学习小程序 AI 能力层，打通 AI 讲词、学习教练、错词复盘、学习报告、RAG 问答等场景。
2. 基于 LangGraph / pipeline 兼容架构实现“学习计划重规划 Agent”，串联用户计划、错词、复习压力、趋势数据和检索知识，输出个性化训练策略。
3. 设计统一 AI evidence 结构，在前端展示 workflow、tools、retrieval hits、latency、cache hit、model/prompt version，增强 AI 结果可解释性。
4. 将业务能力抽象为 MCP 风格 tools/resources/prompts，构建可扩展的 AI 工具层。
5. 实现 AI 请求缓存、限流、运行日志与质量摘要，为后续 tracing、评测与成本治理打下基础。

## 6. 当前仍可继续扩展的方向

后续如果还想继续强化“AI / Agent 项目感”，推荐优先做这几项：

1. Agent 的“应用计划 patch”扩展为完整计划更新与回滚
2. 在 evidence 中加入更细粒度 tool trace 时间线
3. 增加基于会话历史的长期记忆与用户画像更新
4. 接入更正式的向量库与 embedding
5. 增加 AI 评测集、失败样本回放与 tracing 页面

