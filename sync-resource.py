#!/usr/bin/env python3
"""
Code Agents 资源同步工具 - 支持同步单个资源
可以只同步 agents、commands 或 skills 到指定的 code agent
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ResourceSyncer:
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

    def _backup_if_exists(self, path: Path) -> None:
        """备份现有文件或目录"""
        if path.exists() and not path.is_symlink():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.parent / f"{path.name}.backup.{timestamp}"
            shutil.move(str(path), str(backup_path))
            print(f"  📦 备份: {path.name} -> {backup_path.name}")

    def sync_resource(
        self, agent: str, resource: str, strategy: str = "symlink"
    ) -> bool:
        """同步单个资源

        Args:
            agent: 目标 agent (claude-code, opencode, codex)
            resource: 资源类型 (agents, commands, skills)
            strategy: 同步策略 (symlink 或 copy)
        """
        # 验证 agent
        config_dir = self._get_agent_config_dir(agent)
        if not config_dir or not config_dir.exists():
            print(f"❌ {agent} 配置目录不存在: {config_dir}")
            return False

        # 验证 resource
        if resource not in self.config["sharedResources"]:
            print(f"❌ 未知的资源类型: {resource}")
            print(f"可用资源: {', '.join(self.config['sharedResources'].keys())}")
            return False

        # 获取资源映射
        agent_config = self.config["agentCompatibility"][agent]
        resource_mapping = agent_config.get("resourceMapping", {})

        if resource not in resource_mapping:
            print(f"⚠️  {agent} 不支持 {resource} 资源")
            return False

        relative_path = resource_mapping[resource]
        source = (
            self.shared_config_dir / self.config["sharedResources"][resource]["path"]
        )
        # 解析目标路径，支持相对路径（如 ../xxx）
        target = (config_dir / relative_path).resolve()

        print(f"\n{'🔗' if strategy == 'symlink' else '📁'} 同步 {resource} 到 {agent}")
        print(f"  源: {source}")
        print(f"  目标: {target}")
        print(f"  策略: {strategy}")
        print()

        # 确保父目录存在
        target.parent.mkdir(parents=True, exist_ok=True)

        # 备份现有配置
        self._backup_if_exists(target)

        # 删除旧链接
        if target.is_symlink():
            target.unlink()
            print("  🗑️  删除旧符号链接")

        # 执行同步
        if strategy == "symlink":
            target.symlink_to(source)
            print(f"  ✅ 创建符号链接: {target} -> {source}")
        else:  # copy
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
                file_count = sum(1 for _ in source.rglob("*") if _.is_file())
                print(f"  ✅ 复制目录 (包含 {file_count} 个文件)")
            else:
                shutil.copy2(source, target)
                print("  ✅ 复制文件")

        return True

    def list_resources(self) -> None:
        """列出所有可用的资源"""
        print("\n📚 共享资源列表\n")

        for resource, info in self.config["sharedResources"].items():
            path = self.shared_config_dir / info["path"]
            description = info.get("description", "")

            print(f"📦 {resource}")
            print(f"   描述: {description}")
            print(f"   路径: {path}")

            if path.is_dir():
                file_count = sum(1 for _ in path.rglob("*") if _.is_file())
                print(f"   文件数: {file_count}")

            # 显示哪些 agents 支持此资源
            supporting_agents = []
            for agent, agent_config in self.config["agentCompatibility"].items():
                if resource in agent_config.get("resourceMapping", {}):
                    supporting_agents.append(agent)

            print(f"   支持的 agents: {', '.join(supporting_agents)}")
            print()

    def show_resource_status(self, agent: str, resource: str) -> None:
        """显示特定资源的同步状态"""
        config_dir = self._get_agent_config_dir(agent)
        if not config_dir or not config_dir.exists():
            print(f"❌ {agent} 未安装")
            return

        agent_config = self.config["agentCompatibility"][agent]
        resource_mapping = agent_config.get("resourceMapping", {})

        if resource not in resource_mapping:
            print(f"⚠️  {agent} 不支持 {resource}")
            return

        # 解析目标路径，支持相对路径（如 ../xxx）
        target = (config_dir / resource_mapping[resource]).resolve()

        print(f"\n📊 {agent} - {resource} 状态\n")

        if target.is_symlink():
            link_target = target.readlink()
            print("✅ 类型: 符号链接")
            print(f"   指向: {link_target}")
        elif target.is_dir():
            file_count = sum(1 for _ in target.rglob("*") if _.is_file())
            print("📁 类型: 独立目录")
            print(f"   文件数: {file_count}")
        elif target.exists():
            print("📄 类型: 独立文件")
        else:
            print("❌ 状态: 不存在")

        print(f"   路径: {target}")


def main():
    parser = argparse.ArgumentParser(
        description="Code Agents 资源同步工具 - 精确控制单个资源的同步",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 只同步 agents 到 Claude Code (使用符号链接)
  %(prog)s --agent claude-code --resource agents

  # 只同步 skills 到 OpenCode (使用复制)
  %(prog)s --agent opencode --resource skills --strategy copy

  # 列出所有可用资源
  %(prog)s --list-resources

  # 查看 claude-code 的 agents 状态
  %(prog)s --agent claude-code --resource agents --status

  # 同步多个资源到同一个 agent
  %(prog)s --agent codex --resource agents
  %(prog)s --agent codex --resource skills
        """,
    )

    parser.add_argument(
        "--manifest", default="config-manifest.json", help="配置清单文件路径"
    )
    parser.add_argument(
        "--agent", choices=["claude-code", "opencode", "codex"], help="目标 Code Agent"
    )
    parser.add_argument(
        "--resource", choices=["agents", "commands", "skills"], help="要同步的资源类型"
    )
    parser.add_argument(
        "--strategy",
        choices=["symlink", "copy"],
        default="symlink",
        help="同步策略 (默认: symlink)",
    )
    parser.add_argument(
        "--list-resources", action="store_true", help="列出所有可用资源"
    )
    parser.add_argument("--status", action="store_true", help="显示资源状态")

    args = parser.parse_args()

    # 查找 manifest 文件
    manifest_path = Path(__file__).parent / args.manifest
    if not manifest_path.exists():
        print(f"❌ 找不到配置清单: {manifest_path}")
        sys.exit(1)

    syncer = ResourceSyncer(str(manifest_path))

    if args.list_resources:
        syncer.list_resources()
    elif args.status:
        if not args.agent or not args.resource:
            print("❌ --status 需要同时指定 --agent 和 --resource")
            sys.exit(1)
        syncer.show_resource_status(args.agent, args.resource)
    elif args.agent and args.resource:
        success = syncer.sync_resource(args.agent, args.resource, args.strategy)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
