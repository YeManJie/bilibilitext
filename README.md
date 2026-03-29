# Bili2Text

一键将B站视频转换为文字稿并生成AI摘要

## 功能

- ✅ 自动下载B站视频
- ✅ 提取音频并分割
- ✅ Whisper语音转文字
- ✅ Ollama本地大模型生成摘要
- ✅ 输出保存到Windows桌面

## 安装

```bash
# 1. 克隆仓库
git clone https://github.com/YeManJie/bilibilitext.git
cd bili2text

# 2. 运行安装脚本
./install.sh

# 3. 下载模型（如未安装）
ollama pull qwen2.5:7b
```

## 使用

```bash
# 确保Ollama服务在运行
ollama serve

# 转录视频
./start.sh "https://www.bilibili.com/video/BVxxxxx"
```

## 输出文件

处理完成后，会在桌面生成：
- `{视频ID}_transcript.txt` - 完整转录
- `{视频ID}_summary.txt` - 摘要+转录

## 依赖

- Python 3.8+
- FFmpeg
- Ollama
- Whisper (自动安装)

## License

MIT
