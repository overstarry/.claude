#!/bin/bash
# 统一 Code Agents 配置设置脚本
# 支持: Claude Code, OpenCode, Codex 等

set -e

SHARED_CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "共享配置目录: $SHARED_CONFIG_DIR"

# Code agent 配置目录映射
declare -A AGENT_CONFIGS=(
    ["claude-code"]="$HOME/.claude"
    ["opencode"]="$HOME/.opencode"
    ["codex"]="$HOME/.codex"
)

# 需要共享的目录
SHARED_DIRS=("agents" "commands" "skills")

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  Code Agents 共享配置设置工具"
echo "========================================"
echo ""

# 选择操作模式
echo "请选择操作模式:"
echo "1) 创建符号链接 (推荐)"
echo "2) 复制文件"
echo "3) 显示配置状态"
echo "4) 清理链接"
read -p "输入选项 [1-4]: " MODE

case $MODE in
    1)
        echo -e "${YELLOW}创建符号链接模式${NC}"
        for agent in "${!AGENT_CONFIGS[@]}"; do
            config_dir="${AGENT_CONFIGS[$agent]}"

            # 检查 code agent 是否安装
            if [ ! -d "$config_dir" ]; then
                echo "跳过 $agent (未找到配置目录: $config_dir)"
                continue
            fi

            echo -e "${GREEN}配置 $agent${NC}"

            for dir in "${SHARED_DIRS[@]}"; do
                target="$config_dir/$dir"
                source="$SHARED_CONFIG_DIR/$dir"

                # 备份现有配置
                if [ -e "$target" ] && [ ! -L "$target" ]; then
                    backup="$target.backup.$(date +%Y%m%d_%H%M%S)"
                    echo "  备份现有配置: $target -> $backup"
                    mv "$target" "$backup"
                fi

                # 删除旧链接
                if [ -L "$target" ]; then
                    rm "$target"
                fi

                # 创建符号链接
                ln -s "$source" "$target"
                echo "  ✓ 链接: $target -> $source"
            done
            echo ""
        done
        echo -e "${GREEN}符号链接创建完成!${NC}"
        ;;

    2)
        echo -e "${YELLOW}复制文件模式${NC}"
        for agent in "${!AGENT_CONFIGS[@]}"; do
            config_dir="${AGENT_CONFIGS[$agent]}"

            if [ ! -d "$config_dir" ]; then
                echo "跳过 $agent (未找到配置目录: $config_dir)"
                continue
            fi

            echo -e "${GREEN}复制到 $agent${NC}"

            for dir in "${SHARED_DIRS[@]}"; do
                target="$config_dir/$dir"
                source="$SHARED_CONFIG_DIR/$dir"

                # 备份现有配置
                if [ -d "$target" ]; then
                    backup="$target.backup.$(date +%Y%m%d_%H%M%S)"
                    echo "  备份: $target -> $backup"
                    mv "$target" "$backup"
                fi

                # 复制文件
                cp -r "$source" "$target"
                echo "  ✓ 复制: $source -> $target"
            done
            echo ""
        done
        echo -e "${GREEN}文件复制完成!${NC}"
        ;;

    3)
        echo -e "${YELLOW}配置状态${NC}"
        echo ""
        for agent in "${!AGENT_CONFIGS[@]}"; do
            config_dir="${AGENT_CONFIGS[$agent]}"

            if [ ! -d "$config_dir" ]; then
                echo "✗ $agent: 未安装"
                continue
            fi

            echo "✓ $agent: 已安装"

            for dir in "${SHARED_DIRS[@]}"; do
                target="$config_dir/$dir"

                if [ -L "$target" ]; then
                    link_target=$(readlink "$target")
                    echo "  - $dir: 链接 -> $link_target"
                elif [ -d "$target" ]; then
                    echo "  - $dir: 独立目录"
                else
                    echo "  - $dir: 不存在"
                fi
            done
            echo ""
        done
        ;;

    4)
        echo -e "${YELLOW}清理链接模式${NC}"
        for agent in "${!AGENT_CONFIGS[@]}"; do
            config_dir="${AGENT_CONFIGS[$agent]}"

            if [ ! -d "$config_dir" ]; then
                continue
            fi

            echo -e "${GREEN}清理 $agent${NC}"

            for dir in "${SHARED_DIRS[@]}"; do
                target="$config_dir/$dir"

                if [ -L "$target" ]; then
                    rm "$target"
                    echo "  ✓ 删除链接: $target"
                fi
            done
            echo ""
        done
        echo -e "${GREEN}链接清理完成!${NC}"
        ;;

    *)
        echo "无效选项"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "提示: 将以下内容添加到你的 ~/.bashrc 或 ~/.zshrc:"
echo "export CODE_AGENTS_SHARED_CONFIG=\"$SHARED_CONFIG_DIR\""
echo "========================================"
