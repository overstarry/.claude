#!/usr/bin/env python3
"""
同步单个文件或目录到指定 Code Agent
支持精确控制:同步单个 agent、单个 skill、单个 command 等
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class SingleItemSyncer:
    def __init__(self, manifest_path: str):
        self.manifest_path = Path(manifest_path)
        self.config = self._load_manifest()
        self.shared_config_dir = Path(self.config["sharedConfigPath"]).expanduser()

    def _load_manifest(self) -> dict:
        """加载配置清单"""
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_agent_config_dir(self, agent: str) -> Optional[Path]:
        """获取代理配置目录"""
        if agent not in self.config["agentCompatibility"]:
            print(f"⚠️  未知的 agent: {agent}")
            return None

        config_dir = self.config["agentCompatibility"][agent]["configDir"]
        return Path(config_dir).expanduser()

    def _find_skill_md(self, start_path: Path) -> Optional[Path]:
        """递归查找 SKILL.md 文件

        Args:
            start_path: 开始搜索的目录

        Returns:
            SKILL.md 文件的路径，如果找不到则返回 None
        """
        # 首先检查当前目录
        skill_md = start_path / "SKILL.md"
        if skill_md.exists():
            return skill_md

        # 递归搜索子目录（最多3层深度，避免无限递归）
        for depth in range(3):
            for item in start_path.rglob("SKILL.md"):
                # 排除隐藏目录
                if not any(part.startswith('.') for part in item.parts):
                    return item

        return None

    def _backup_if_exists(self, path: Path) -> None:
        """备份现有文件或目录"""
        if path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.parent / f"{path.name}.backup.{timestamp}"

            if path.is_symlink():
                # 符号链接只需删除,不需要备份
                path.unlink()
                print(f"  🗑️  删除旧符号链接: {path.name}")
            else:
                shutil.move(str(path), str(backup_path))
                print(f"  📦 备份: {path.name} -> {backup_path.name}")

    def sync_item(
        self, agent: str, resource_type: str, item_name: str, strategy: str = "symlink"
    ) -> bool:
        """同步单个项目

        Args:
            agent: 目标 agent (claude-code, opencode, codex)
            resource_type: 资源类型 (agents, commands, skills)
            item_name: 项目名称 (如 'seo-optimizer', 'code-reviewer.md')
            strategy: 同步策略 (symlink 或 copy)
        """
        # 验证 agent
        config_dir = self._get_agent_config_dir(agent)
        if not config_dir or not config_dir.exists():
            print(f"❌ {agent} 配置目录不存在: {config_dir}")
            print("\n💡 提示: 请先创建目录:")
            print(f"   mkdir -p {config_dir}")
            return False

        # 验证 resource_type
        if resource_type not in self.config["sharedResources"]:
            print(f"❌ 未知的资源类型: {resource_type}")
            print(f"可用类型: {', '.join(self.config['sharedResources'].keys())}")
            return False

        # 获取源路径
        source_base = (
            self.shared_config_dir
            / self.config["sharedResources"][resource_type]["path"]
        )
        source = source_base / item_name

        # 检查嵌套 skills
        if resource_type == "skills" and not source.exists():
            nested_skills = self.config["sharedResources"]["skills"].get("nestedSkills", {})
            for group_name, group_config in nested_skills.items():
                if item_name in group_config.get("skills", []):
                    source = source_base / group_config["basePath"] / item_name
                    print(f"💡 找到嵌套 skill: {group_name}/{item_name}")
                    break

        # 对于 skills，检查是否有 agent 专用目录结构 (如 .codex/skills/<item>/)
        if resource_type == "skills" and source.is_dir():
            agent_dir_map = {
                "claude-code": ".claude",
                "codex": ".codex",
                "opencode": ".opencode",
            }
            agent_subdir = agent_dir_map.get(agent)
            if agent_subdir:
                agent_skill_path = source / agent_subdir / "skills" / item_name
                if agent_skill_path.is_dir():
                    print(f"💡 检测到 agent 专用 skill 结构")
                    print(f"   从: {source}")
                    print(f"   到: {agent_skill_path}")
                    source = agent_skill_path
                else:
                    # 回退到查找 SKILL.md
                    skill_md = self._find_skill_md(source)
                    if skill_md:
                        actual_source = skill_md.parent
                        if actual_source != source:
                            print(f"💡 检测到嵌套 skill 结构")
                            print(f"   从: {source}")
                            print(f"   到: {actual_source}")
                            source = actual_source
                    elif not (source / "SKILL.md").exists():
                        print(f"⚠️  警告: 在 {source} 中找不到 SKILL.md 文件")

        if not source.exists():
            print(f"❌ 源不存在: {source}")
            print(f"\n💡 可用的 {resource_type}:")
            self._list_items(resource_type)
            return False

        # 获取目标路径
        agent_config = self.config["agentCompatibility"][agent]
        resource_mapping = agent_config.get("resourceMapping", {})

        if resource_type not in resource_mapping:
            print(f"⚠️  {agent} 不支持 {resource_type} 资源")
            return False

        # 解析目标路径，支持相对路径（如 ../xxx）
        target_base = (config_dir / resource_mapping[resource_type]).resolve()
        target = target_base / item_name

        print(
            f"\n{'🔗' if strategy == 'symlink' else '📁'} 同步 {resource_type}/{item_name}"
        )
        print(f"  源: {source}")
        print(f"  目标: {target}")
        print(f"  策略: {strategy}")
        print()

        # 确保目标目录存在
        target_base.mkdir(parents=True, exist_ok=True)

        # 备份现有配置
        self._backup_if_exists(target)

        # 执行同步
        if strategy == "symlink":
            target.symlink_to(source)
            print("  ✅ 创建符号链接")
        else:  # copy
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
                file_count = sum(1 for _ in source.rglob("*") if _.is_file())
                print(f"  ✅ 复制目录 (包含 {file_count} 个文件)")
            else:
                shutil.copy2(source, target)
                print("  ✅ 复制文件")

        print("\n✨ 完成!")
        return True

    def _list_items(self, resource_type: str) -> None:
        """列出指定类型的所有项目"""
        source_base = (
            self.shared_config_dir
            / self.config["sharedResources"][resource_type]["path"]
        )

        if not source_base.exists():
            print("   (空)")
            return

        items = []
        for item in source_base.iterdir():
            if item.name.startswith("."):
                continue
            items.append(item.name)

        if items:
            for item in sorted(items):
                print(f"   - {item}")
        else:
            print("   (空)")

        # 显示嵌套 skills
        if resource_type == "skills":
            nested_skills = self.config["sharedResources"]["skills"].get("nestedSkills", {})
            for group_name, group_config in nested_skills.items():
                skills = group_config.get("skills", [])
                if skills:
                    print(f"   [{group_name}]")
                    for skill in sorted(skills):
                        print(f"     - {skill}")

    def list_all_items(self) -> None:
        """列出所有可用的项目"""
        print("\n📚 可用的配置项目\n")

        for resource_type in self.config["sharedResources"].keys():
            print(f"📦 {resource_type}:")
            self._list_items(resource_type)
            print()

    def show_item_status(self, agent: str, resource_type: str, item_name: str) -> None:
        """显示特定项目的同步状态"""
        config_dir = self._get_agent_config_dir(agent)
        if not config_dir or not config_dir.exists():
            print(f"❌ {agent} 未安装")
            return

        agent_config = self.config["agentCompatibility"][agent]
        resource_mapping = agent_config.get("resourceMapping", {})

        if resource_type not in resource_mapping:
            print(f"⚠️  {agent} 不支持 {resource_type}")
            return

        # 解析目标路径，支持相对路径（如 ../xxx）
        target_base = (config_dir / resource_mapping[resource_type]).resolve()
        target = target_base / item_name

        print(f"\n📊 {agent} - {resource_type}/{item_name} 状态\n")

        if target.is_symlink():
            link_target = target.readlink()
            print("✅ 类型: 符号链接")
            print(f"   指向: {link_target}")
        elif target.is_dir():
            file_count = sum(1 for _ in target.rglob("*") if _.is_file())
            print("📁 类型: 独立目录")
            print(f"   文件数: {file_count}")
        elif target.exists():
            size = target.stat().st_size
            print("📄 类型: 独立文件")
            print(f"   大小: {size} 字节")
        else:
            print("❌ 状态: 不存在")

        print(f"   路径: {target}")


def main():
    parser = argparse.ArgumentParser(
        description="同步单个配置项到 Code Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 只同步 seo-optimizer skill 到 Claude Code
  %(prog)s --agent claude-code --type skills --item seo-optimizer

  # 只同步 code-reviewer.md agent 到 OpenCode
  %(prog)s --agent opencode --type agents --item code-reviewer.md

  # 使用复制模式同步
  %(prog)s --agent codex --type skills --item frontend-design --strategy copy

  # 查看状态
  %(prog)s --agent claude-code --type skills --item seo-optimizer --status

  # 列出所有可用项目
  %(prog)s --list
        """,
    )

    parser.add_argument(
        "--manifest", default="config-manifest.json", help="配置清单文件路径"
    )
    parser.add_argument(
        "--agent", choices=["claude-code", "opencode", "codex"], help="目标 Code Agent"
    )
    parser.add_argument(
        "--type", choices=["agents", "commands", "skills"], help="资源类型"
    )
    parser.add_argument("--item", help="项目名称 (如 seo-optimizer, code-reviewer.md)")
    parser.add_argument(
        "--strategy",
        choices=["symlink", "copy"],
        default="symlink",
        help="同步策略 (默认: symlink)",
    )
    parser.add_argument("--list", action="store_true", help="列出所有可用项目")
    parser.add_argument("--status", action="store_true", help="显示项目状态")

    args = parser.parse_args()

    # 查找 manifest 文件
    manifest_path = Path(__file__).parent / args.manifest
    if not manifest_path.exists():
        print(f"❌ 找不到配置清单: {manifest_path}")
        sys.exit(1)

    syncer = SingleItemSyncer(str(manifest_path))

    if args.list:
        syncer.list_all_items()
    elif args.status:
        if not args.agent or not args.type or not args.item:
            print("❌ --status 需要同时指定 --agent, --type 和 --item")
            sys.exit(1)
        syncer.show_item_status(args.agent, args.type, args.item)
    elif args.agent and args.type and args.item:
        success = syncer.sync_item(args.agent, args.type, args.item, args.strategy)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
