# Code Agents 共享配置仓库

在 Claude Code、OpenCode、Codex 等多个 Code Agent 之间共享 agents、commands、skills 配置。

## 目录结构

```
.claude/
├── agents/                  # AI 代理配置
├── commands/                # 自定义命令
├── skills/                  # 技能配置
├── config-manifest.json     # 配置清单
├── sync-config.py          # 批量同步工具
├── sync-resource.py        # 资源类型同步
├── sync-single.py          # 单个项目同步
└── test-config.sh          # 配置测试脚本
```

## 快速开始

### 同步工具对比

| 工具               | 同步粒度                          | 使用场景           |
| ------------------ | --------------------------------- | ------------------ |
| `sync-config.py`   | 所有配置                          | 首次设置、批量更新 |
| `sync-resource.py` | 资源类型 (agents/commands/skills) | 只需要某一类资源   |
| `sync-single.py`   | 单个文件/目录                     | 最精细控制         |

### 常用命令

```bash
# 查看当前状态
./sync-config.py --status

# 同步所有配置到所有 agents
./sync-config.py --sync-all

# 同步所有配置到指定 agent
./sync-config.py --agent claude-code

# 只同步 skills 资源
./sync-resource.py --agent claude-code --resource skills

# 只同步 seo-optimizer skill
./sync-single.py --agent claude-code --type skills --item seo-optimizer

# 查看可用项目
./sync-single.py --list
```

### 使用示例

```bash
# 场景 1: 首次设置 Claude Code
./sync-config.py --agent claude-code

# 场景 2: 只想使用 SEO 优化功能
./sync-single.py --agent claude-code --type skills --item seo-optimizer

# 场景 3: 查看 seo-optimizer 同步状态
./sync-single.py --agent claude-code --type skills --item seo-optimizer --status

# 场景 4: 使用复制模式 (而非符号链接)
./sync-single.py --agent claude-code --type skills --item seo-optimizer --strategy copy

# 场景 5: 同步 UI/UX Pro Max 设计智能系统
./sync-single.py --agent claude-code --type skills --item ui-ux-pro-max

# 场景 6: 同步所有前端相关 skills
./sync-single.py --agent claude-code --type skills --item frontend-design
./sync-single.py --agent claude-code --type skills --item ui-ux-pro-max
./sync-single.py --agent claude-code --type skills --item seo-optimizer
```

## 支持的 Code Agents

- **Claude Code** (`~/.claude/`)
- **OpenCode** (`~/.opencode/`)
- **Codex** (`~/.codex/`)

## 配置资源

### Agents

- code-reviewer.md - 代码审查
- frontend-developer.md - 前端开发
- seo-analyzer.md - SEO 分析
- ui-ux-designer.md - UI/UX 设计

### Skills

- [frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) - 前端设计
- [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) - UI/UX 设计智能系统 (50+ 样式、21 种配色、50 种字体组合、20 种图表)
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) - 规划与文件管理 (Git Submodule)
- seo-optimizer - SEO 优化

## Git Submodule 管理

本仓库使用 Git Submodule 引入外部 skills，便于保持与上游仓库同步。

### 常用命令

```bash
# 克隆项目时（包含所有 submodules）
git clone --recursive <repo-url>

# 已克隆后初始化 submodules
git submodule update --init --recursive

# 更新指定 submodule 到最新版本
git submodule update --remote skills/planning-with-files

# 更新所有 submodules
git submodule update --remote

# 查看 submodule 状态
git submodule status
```

### Commands

- fix-github-issue.md - 修复 GitHub Issue

## 同步策略

- **符号链接** (默认): 自动同步,修改一处全部生效,节省空间
- **文件复制**: 完全独立,需手动重新同步

使用 `--strategy copy` 切换到复制模式。

## 许可证

MIT
