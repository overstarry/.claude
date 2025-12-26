#!/usr/bin/env python3
"""
Code Agents 配置同步工具
支持多种同步策略: 符号链接、文件复制、Git 子模块
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ConfigSyncer:
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

    def sync_symlink(self, agent: str) -> bool:
        """使用符号链接同步"""
        config_dir = self._get_agent_config_dir(agent)
        if not config_dir or not config_dir.exists():
            print(f"⏭️  跳过 {agent} (配置目录不存在: {config_dir})")
            return False

        print(f"\n🔗 同步 {agent} (符号链接模式)")

        agent_config = self.config["agentCompatibility"][agent]
        resource_mapping = agent_config.get("resourceMapping", {})

        for resource, relative_path in resource_mapping.items():
            if resource not in self.config["sharedResources"]:
                continue

            source = (
                self.shared_config_dir
                / self.config["sharedResources"][resource]["path"]
            )
            target = config_dir / relative_path

            # 确保父目录存在
            target.parent.mkdir(parents=True, exist_ok=True)

            # 备份现有配置
            self._backup_if_exists(target)

            # 删除旧链接
            if target.is_symlink():
                target.unlink()

            # 创建符号链接
            target.symlink_to(source)
            print(f"  ✅ {resource}: {target} -> {source}")

        return True

    def sync_copy(self, agent: str) -> bool:
        """使用文件复制同步"""
        config_dir = self._get_agent_config_dir(agent)
        if not config_dir or not config_dir.exists():
            print(f"⏭️  跳过 {agent} (配置目录不存在: {config_dir})")
            return False

        print(f"\n📁 同步 {agent} (复制模式)")

        agent_config = self.config["agentCompatibility"][agent]
        resource_mapping = agent_config.get("resourceMapping", {})

        for resource, relative_path in resource_mapping.items():
            if resource not in self.config["sharedResources"]:
                continue

            source = (
                self.shared_config_dir
                / self.config["sharedResources"][resource]["path"]
            )
            target = config_dir / relative_path

            # 确保父目录存在
            target.parent.mkdir(parents=True, exist_ok=True)

            # 备份现有配置
            self._backup_if_exists(target)

            # 复制文件或目录
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)

            print(f"  ✅ {resource}: {source} -> {target}")

        return True

    def show_status(self) -> None:
        """显示配置状态"""
        print("\n📊 Code Agents 配置状态\n")
        print(f"共享配置目录: {self.shared_config_dir}\n")

        for agent in self.config["supportedAgents"]:
            config_dir = self._get_agent_config_dir(agent)

            if not config_dir:
                continue

            if not config_dir.exists():
                print(f"❌ {agent}: 未安装 ({config_dir})")
                continue

            print(f"✅ {agent}: 已安装")

            agent_config = self.config["agentCompatibility"].get(agent, {})
            resource_mapping = agent_config.get("resourceMapping", {})

            for resource, relative_path in resource_mapping.items():
                target = config_dir / relative_path

                if target.is_symlink():
                    link_target = target.readlink()
                    print(f"   🔗 {resource}: 链接 -> {link_target}")
                elif target.exists():
                    print(f"   📁 {resource}: 独立目录")
                else:
                    print(f"   ⚠️  {resource}: 不存在")

            print()

    def cleanup_links(self, agent: Optional[str] = None) -> None:
        """清理符号链接"""
        agents_to_clean = [agent] if agent else self.config["supportedAgents"]

        print("\n🧹 清理符号链接\n")

        for agent_name in agents_to_clean:
            config_dir = self._get_agent_config_dir(agent_name)
            if not config_dir or not config_dir.exists():
                continue

            print(f"清理 {agent_name}")

            agent_config = self.config["agentCompatibility"].get(agent_name, {})
            resource_mapping = agent_config.get("resourceMapping", {})

            for resource, relative_path in resource_mapping.items():
                target = config_dir / relative_path

                if target.is_symlink():
                    target.unlink()
                    print(f"  ✅ 删除: {resource}")

            print()

    def sync_all(self, strategy: str = "symlink") -> None:
        """同步所有 agents"""
        print(f"\n🚀 开始同步所有 Code Agents (策略: {strategy})\n")

        sync_func = self.sync_symlink if strategy == "symlink" else self.sync_copy

        success_count = 0
        for agent in self.config["supportedAgents"]:
            if sync_func(agent):
                success_count += 1

        print(f"\n✨ 完成! 成功同步 {success_count} 个 agents")


def main():
    parser = argparse.ArgumentParser(
        description="Code Agents 配置同步工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --status                    # 查看配置状态
  %(prog)s --sync-all                  # 同步所有 agents (使用符号链接)
  %(prog)s --sync-all --strategy copy  # 同步所有 agents (使用复制)
  %(prog)s --agent claude-code         # 同步指定 agent
  %(prog)s --cleanup                   # 清理所有符号链接
        """,
    )

    parser.add_argument(
        "--manifest", default="config-manifest.json", help="配置清单文件路径"
    )
    parser.add_argument("--status", action="store_true", help="显示配置状态")
    parser.add_argument("--sync-all", action="store_true", help="同步所有 agents")
    parser.add_argument("--agent", help="同步指定的 agent")
    parser.add_argument(
        "--strategy",
        choices=["symlink", "copy"],
        default="symlink",
        help="同步策略 (默认: symlink)",
    )
    parser.add_argument("--cleanup", action="store_true", help="清理符号链接")

    args = parser.parse_args()

    # 查找 manifest 文件
    manifest_path = Path(__file__).parent / args.manifest
    if not manifest_path.exists():
        print(f"❌ 找不到配置清单: {manifest_path}")
        sys.exit(1)

    syncer = ConfigSyncer(str(manifest_path))

    if args.status:
        syncer.show_status()
    elif args.sync_all:
        syncer.sync_all(args.strategy)
    elif args.agent:
        if args.strategy == "symlink":
            syncer.sync_symlink(args.agent)
        else:
            syncer.sync_copy(args.agent)
    elif args.cleanup:
        syncer.cleanup_links()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
