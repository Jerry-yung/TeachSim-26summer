# TeachSim Git 合作开发记录

本文档依据 TeachSim 仓库的真实 Git 历史整理，用于展示项目成员在前端、业务后端、AI 服务和项目文档方面的分工协作，以及 branches、commits、merges 和 tags 等合作开发要素。

---

## 一、仓库概况

- 项目名称：TeachSim-26summer
- 远程仓库：[Jerry-yung/TeachSim-26summer](https://github.com/Jerry-yung/TeachSim-26summer)
- 默认分支：`main`
- 开发记录时间：2026-07-15 至 2026-07-23
- Git 提交总数：35


项目使用根目录下的 `frontend/`、`backend/`、`ai/` 和 `docs/` 作为统一开发主线，并通过功能提交、开发分支合并和里程碑 Tag 保存各阶段成果。

---

## 二、成员分工与 Git 身份

| 项目成员 | Git 作者身份 |  主要负责内容 |
|---|---|------|
| 刘至晗 | `Weirdo0411` |  Vue 前端、课堂主链路、ASR/TTS 交互、视觉采集与报告展示 |
| 唐一嘉 | `Daydream` |  FastAPI 业务后端、认证、课堂状态、历史报告、语音与视觉接口 |
| 杨云天 | `Jerry-yung`|  AI 服务、Supervisor、学生 Agent、课前解析、课后报告与视觉模型 |
| 周光轩 | `zhou guangxuan` |  项目文档、README、文档结构整理与最终定稿 |



---

## 三、分支与合并协作

项目以 `main` 作为稳定主线，业务后端开发使用过 `dev-backend` 分支。后端功能经过独立开发后，通过 Merge Commit 合并回主线。

| 日期 | Merge Commit | 作者 | 合并内容 |
|---|---|---|---|
| 2026-07-20 | `a1b7b71` | Daydream | `Merge branch 'dev-backend'`，合并课堂交互、报告增强、PPT 预览和项目结构调整 |
| 2026-07-23 | `7e93053` | Daydream | `Merge branch 'dev-backend'`，合并认证、ASR、TTS、举手策略和视觉分析路由 |

这两次合并体现了“开发分支完成模块功能—合并进入 main—前端与 AI 服务继续联调”的协作方式。

---



## 四、典型合作开发过程

### 1. 课前到课后完整课堂主链路

1. 杨云天完成 AI v2 主体架构和课前、课中、课后 Agent；
2. 唐一嘉完成课程、课堂、报告、ASR 调试和数据库服务；
3. 刘至晗完成登录、课前配置、虚拟课堂和报告页面联调；
4. 周光轩同步整理 README、API 和开发文档。



### 2. 虚拟学生课堂互动

1. 业务后端建立虚拟学生状态库和课堂交互状态机；
2. AI 服务升级 Supervisor 决策、提问难度判断和学生回复；
3. 前端根据举手、点名、纪律状态和学生语音更新课堂界面。

代表提交：

- `8c866dc`：课堂学生状态库与交互状态机；
- `efef913`：学生回复、纪律互斥与决策日志；
- `1a89345`：AI 课中决策与学生互动升级；
- `b689547`：举手策略和课堂交互增强。

### 3. 实时语音协作链路

1. 业务后端提供讯飞签名、MiniMax TTS 和认证保护；
2. 前端建立讯飞实时 ASR，并控制学生语音播放期间的识别状态；
3. AI 服务根据教师发言生成学生回复。

代表提交：

- `1ed4e5b`：前端 ASR 续听和 MiniMax TTS 播放联动；
- `121c6f6`：后端认证、ASR、TTS 和邮箱模块；
- `2505850`：教师注册登录与认证。

### 4. 教姿教态视觉分析

视觉分析由三个模块共同完成：

```text
前端采集摄像头窗口、抽样帧和 WebM 短片
  → 业务后端保存视觉观察并调用 AI 服务
  → AI 多模态模型分析站姿、手势、表情和视线
  → 业务后端汇总视觉结果到课后报告
  → 前端展示教姿教态得分和时间轴
```

代表提交：

- `699c91c`：前端接入视觉采集与报告展示；
- `c653911`：AI 新增教姿教态视觉分析；
- `b689547`：后端新增视觉分析路由并增强课堂交互；
- `7e93053`：`dev-backend` 合并进入主线。

---

## 五、完整 Commit 记录

以下记录按时间倒序排列，覆盖当前仓库全部 35 个 Commit。

| 日期 | Commit | 作者 | 提交内容 |
|---|---|---|---|
| 2026-07-23 | `3b532b4` | zhou guangxuan | 修改并最终的文档定稿 |
| 2026-07-23 | `7e93053` | Daydream | Merge branch `dev-backend` |
| 2026-07-23 | `b689547` | Daydream | feat(backend)：举手策略、视觉分析路由与课堂交互增强 |
| 2026-07-22 | `c653911` | Jerry-yung | feat(ai)：新增课中教姿教态视觉分析（week-0722） |
| 2026-07-22 | `7bcc495` | Weirdo0411 | docs：补充 week-0722-frontend 里程碑说明 |
| 2026-07-22 | `699c91c` | Weirdo0411 | feat(frontend)：接入课中视觉教态采集与报告展示 |
| 2026-07-21 | `121c6f6` | Daydream | feat(backend)：补充认证、ASR、TTS、邮箱完整后端模块 |
| 2026-07-21 | `3bf7506` | Weirdo0411 | docs：补充 week-0721-frontend 里程碑说明 |
| 2026-07-21 | `1ed4e5b` | Weirdo0411 | feat(frontend)：强化课中 ASR 续听与 MiniMax TTS 播放联动 |
| 2026-07-21 | `2505850` | Daydream | feat(backend)：教师注册登录与 JWT 认证 |
| 2026-07-20 | `60d20c3` | Daydream | fix(backend)：修复 `.env` 加载路径 |
| 2026-07-20 | `cd25944` | Jerry-yung | feat(ai)：同步 AI 模块至 week-0720 里程碑 |
| 2026-07-20 | `a1b7b71` | Daydream | Merge branch `dev-backend` |
| 2026-07-20 | `5a9ff92` | Daydream | feat(backend)：新增历史对比、PPT 预览、认证守卫与报告增强 |
| 2026-07-20 | `b36bc4f` | Daydream | chore：调整项目结构 |
| 2026-07-20 | `4805a7b` | zhou guangxuan | 完善文档并删除旧储存文件夹 |
| 2026-07-19 | `3a3c8d9` | Daydream | feat(backend)：并发 PPT 解析、课堂重启、报告高亮上下文与批处理优化 |
| 2026-07-19 | `1a89345` | Jerry-yung | feat(ai)：升级课中决策与学生互动能力（week-0719） |
| 2026-07-19 | `c27a2e2` | Jerry-yung | chore(ai)：将 AI 模块迁移至根目录 |
| 2026-07-19 | `483978f` | Daydream | chore(backend)：将业务后端迁移至根目录 |
| 2026-07-19 | `3046679` | Weirdo0411 | docs：简化仓库结构说明，移除状态列 |
| 2026-07-19 | `dc37ae0` | Weirdo0411 | docs：补充 week-0715 里程碑说明 |
| 2026-07-19 | `1d20886` | Weirdo0411 | refactor：将前端迁至仓库根目录并统一开发主线 |
| 2026-07-19 | `efef913` | Daydream | feat(backend)：增强课堂交互状态机、学生回复、纪律互斥和决策日志 |
| 2026-07-19 | `c7870a8` | Weirdo0411 | docs：更新本周进度说明与前端目录介绍 |
| 2026-07-19 | `5a5e1fd` | Weirdo0411 | feat(frontend)：打通课前到报告的完整课堂主链路 |
| 2026-07-17 | `8c866dc` | Daydream | feat(backend)：实现课堂学生状态库与完整交互状态机 |
| 2026-07-16 | `53a8057` | zhou guangxuan | 修改 README |
| 2026-07-16 | `0dd6330` | zhou guangxuan | 完成文档修改 |
| 2026-07-15 | `75b6a76` | Daydream | feat(backend)：建立 FastAPI、数据库、迁移、课堂、课程、报告、ASR 和 AI 客户端等业务后端结构 |
| 2026-07-15 | `c34622d` | Weirdo0411 | feat(frontend)：完成登录鉴权、课堂可视化与 AI、ASR 接口联调 |
| 2026-07-15 | `0f81cc5` | Jerry-yung | feat(ai)：更新 AI 模块为 v2 架构 |
| 2026-07-15 | `eeaa0c9` | Yuntian Yang | 更新 README |
| 2026-07-15 | `200c230` | Jerry-yung | feat：初始化项目主体架构 |
| 2026-07-15 | `387e5c4` | Yuntian Yang | Initial commit |

---

## 六、提交类型与协作规范

项目提交信息使用了清晰的类型前缀：

| 类型 | 说明 | 示例 |
|---|---|---|
| `feat` | 新增功能 | `feat(frontend)`、`feat(backend)`、`feat(ai)` |
| `fix` | 修复问题 | 修复 `.env` 加载路径 |
| `refactor` | 重构目录或代码组织 | 前端迁入根目录 |
| `chore` | 工程结构和维护性调整 | AI、后端目录迁移 |
| `docs` | 文档和里程碑说明 | 更新 README、补充 Tag 说明 |
| `Merge` | 合并开发分支 | Merge branch `dev-backend` |

模块范围 `frontend`、`backend` 和 `ai` 直接体现在提交信息中，使成员能够快速判断改动范围和联调影响。

---

## 七、Git 记录复现命令

在仓库根目录执行以下命令，可以复现本文档使用的 Git 证据：

```bash
# 更新远程分支和 Tags
git fetch --all --prune --tags

# 查看全部分支的提交图
git log --all --graph --decorate --date=short \
  --pretty=format:"%h | %ad | %an | %s"

# 查看合并记录
git log --all --merges --date=short \
  --pretty=format:"%h | %ad | %an | %s"

```

---

##  八、合作开发总结

TeachSim 的 Git 历史完整记录了四名成员围绕前端、业务后端、AI 服务和文档开展的模块化协作。项目从主体架构出发，依次完成课堂主链路、虚拟学生互动、认证与历史报告、实时语音、视觉教态分析和最终文档定稿。开发分支合并、规范化 Commit 和阶段性 Tags 共同形成了可回溯、可比较、可展示的合作开发过程。
