#!/bin/bash
# Bili2Text 一键安装脚本
# 用法: ./install.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "  Bili2Text 安装脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "[1/6] 检查系统环境..."

# 检查操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    echo -e "${YELLOW}警告: 未识别的操作系统: $OSTYPE${NC}"
    OS="unknown"
fi

echo "  检测到操作系统: $OS"

# 检查 Python3
echo "[2/6] 检查 Python3..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "  ${GREEN}✓ Python3 已安装: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python3 未安装${NC}"
    echo "  请安装 Python3.8 或更高版本:"
    echo "    Ubuntu/Debian: sudo apt-get install python3 python3-venv python3-pip"
    echo "    macOS: brew install python3"
    exit 1
fi

# 检查 FFmpeg
echo "[3/6] 检查 FFmpeg..."
if command_exists ffmpeg; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
    echo -e "  ${GREEN}✓ FFmpeg 已安装: $FFMPEG_VERSION${NC}"
else
    echo -e "${YELLOW}✗ FFmpeg 未安装${NC}"
    echo "  正在尝试安装 FFmpeg..."
    
    if [[ "$OS" == "linux" ]]; then
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        elif command_exists yum; then
            sudo yum install -y ffmpeg
        elif command_exists pacman; then
            sudo pacman -S ffmpeg
        else
            echo -e "${RED}错误: 无法自动安装 FFmpeg，请手动安装${NC}"
            exit 1
        fi
    else
        echo -e "${RED}错误: 请手动安装 FFmpeg 并添加到 PATH${NC}"
        echo "  下载地址: https://ffmpeg.org/download.html"
        exit 1
    fi
fi

# 检查 Ollama
echo "[4/6] 检查 Ollama..."
OLLAMA_INSTALLED=false
if command_exists ollama; then
    echo -e "  ${GREEN}✓ Ollama 已安装${NC}"
    OLLAMA_INSTALLED=true
    
    # 检查 Ollama 服务是否运行
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Ollama 服务正在运行${NC}"
    else
        echo -e "${YELLOW}  ⚠ Ollama 服务未启动${NC}"
        echo "    请运行: ollama serve"
    fi
else
    echo -e "${YELLOW}✗ Ollama 未安装${NC}"
    echo "  请安装 Ollama:"
    echo "    Linux: curl -fsSL https://ollama.com/install.sh | sh"
    echo "    macOS: brew install ollama"
    echo "    Windows: https://ollama.com/download"
fi

# 创建虚拟环境并安装 Python 依赖
echo "[5/6] 创建 Python 虚拟环境..."
if [ -d "venv" ]; then
    echo "  虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    echo -e "  ${GREEN}✓ 虚拟环境创建成功${NC}"
fi

echo "[6/6] 安装 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel -q

# 安装核心依赖
echo "  安装核心依赖 (这可能需要几分钟)..."
pip install -q whisper openai-whisper you-get requests pydub moviepy ollama 2>/dev/null || {
    echo "  安装完整依赖集失败，尝试安装精简版..."
    pip install -q openai-whisper ollama you-get pydub
}

echo -e "  ${GREEN}✓ Python 依赖安装完成${NC}"

# 检查模型
echo ""
echo "=========================================="
echo "  安装检查完成！"
echo "=========================================="
echo ""

if [ "$OLLAMA_INSTALLED" = true ]; then
    echo "检查 Qwen 模型..."
    if ollama list | grep -q "qwen2.5"; then
        echo -e "  ${GREEN}✓ Qwen2.5 模型已安装${NC}"
    else
        echo -e "${YELLOW}⚠ Qwen2.5 模型未安装${NC}"
        echo "  请运行以下命令下载模型:"
        echo "    ollama pull qwen2.5:7b"
        echo ""
        echo "  或使用其他模型:"
        echo "    ollama pull qwen2.5:1.8b  (更小，速度更快)"
    fi
else
    echo -e "${YELLOW}⚠ 请先安装 Ollama 并下载模型${NC}"
fi

echo ""
echo "=========================================="
echo "  使用方法"
echo "=========================================="
echo ""
echo "1. 确保 Ollama 服务正在运行:"
echo "   ollama serve"
echo ""
echo "2. 转录B站视频:"
echo "   ./start.sh 'https://www.bilibili.com/video/BVxxxxx'"
echo ""
echo "3. 生成的文件将保存在:"
echo "   - Windows桌面 (如果在WSL中运行)"
echo "   - ./outputs 目录 (其他环境)"
echo ""
echo -e "${GREEN}安装完成！${NC}"
