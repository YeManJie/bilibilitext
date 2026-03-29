#!/usr/bin/env python3
"""
Bili2Text 命令行版本 - 一键生成视频文案和摘要
用法: python run.py <B站视频链接>
"""
import sys
import os
import re
import threading
from pathlib import Path

# Windows桌面路径
DESKTOP_PATH = "/mnt/c/Users/Lenovo/Desktop"

def get_desktop_path():
    """获取Windows桌面路径"""
    if os.path.exists(DESKTOP_PATH):
        return DESKTOP_PATH
    # 回退到项目目录
    return "outputs"

def main():
    if len(sys.argv) < 2:
        print("用法: python run.py <B站视频链接>")
        print("示例: python run.py https://www.bilibili.com/video/BV1xx411c7mD")
        sys.exit(1)
    
    video_link = sys.argv[1]
    
    # 提取BV号
    pattern = r'BV[A-Za-z0-9]+'
    matches = re.findall(pattern, video_link)
    if not matches:
        print("错误: 无效的视频链接，无法提取BV号")
        sys.exit(1)
    
    bv_number = matches[0]
    print(f"视频链接: {video_link}")
    print(f"BV号: {bv_number}")
    print("=" * 50)
    
    # 导入模块
    from utils import download_video
    from exAudio import process_audio_split
    import speech2text
    from summarizer import create_summarizer
    
    # 步骤1: 下载视频
    print("[1/4] 正在下载视频...")
    try:
        file_identifier = download_video(bv_number[2:])
        print(f"视频下载完成: {file_identifier}")
    except Exception as e:
        print(f"下载视频失败: {e}")
        sys.exit(1)
    
    print("=" * 50)
    
    # 步骤2: 分割音频
    print("[2/4] 正在分割音频...")
    try:
        folder_name = process_audio_split(file_identifier)
        print(f"音频分割完成: {folder_name}")
    except Exception as e:
        print(f"分割音频失败: {e}")
        sys.exit(1)
    
    print("=" * 50)
    
    # 步骤3: 语音转文字
    print("[3/4] 正在加载Whisper模型并转录...")
    desktop = get_desktop_path()
    output_filename = f"{file_identifier}_transcript.txt"
    output_path = os.path.join(desktop, output_filename)
    
    # 加载Whisper模型（使用tiny模型加快处理速度）
    speech2text.load_whisper(model="tiny")
    
    # 获取音频文件列表
    audio_dir = f"audio/slice/{folder_name}"
    if not os.path.exists(audio_dir):
        print(f"错误: 音频目录不存在: {audio_dir}")
        sys.exit(1)
    
    audio_files = sorted(
        [f for f in os.listdir(audio_dir) if f.endswith('.mp3')],
        key=lambda x: int(os.path.splitext(x)[0])
    )
    
    print(f"找到 {len(audio_files)} 个音频片段")
    
    # 转录并写入文件
    full_text = []
    for i, fn in enumerate(audio_files, 1):
        print(f"正在转录第{i}/{len(audio_files)}个音频...")
        result = speech2text.whisper_model.transcribe(
            f"{audio_dir}/{fn}",
            initial_prompt=f"以下是普通话的句子。这是一个关于{file_identifier}的视频。"
        )
        text = "".join([seg["text"] for seg in result["segments"] if seg is not None])
        full_text.append(text)
        print(f"  -> {text[:80]}...")
    
    # 保存完整转录文本到桌面
    transcript = "\n".join(full_text)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"视频链接: {video_link}\n")
        f.write(f"BV号: {bv_number}\n")
        f.write("=" * 50 + "\n\n")
        f.write(transcript)
    
    print(f"转录完成！已保存至: {output_path}")
    print("=" * 50)
    
    # 步骤4: 生成摘要
    print("[4/4] 正在连接Ollama生成摘要...")
    try:
        summarizer = create_summarizer(model="qwen2.5:7b")
        
        if not summarizer.is_available():
            print("警告: Ollama服务未启动，跳过摘要生成")
            print("请先启动Ollama: ollama serve")
            return
        
        if not summarizer.check_model_exists():
            print("警告: 模型未找到，请先执行: ollama pull qwen2.5:7b")
            return
        
        print("正在生成摘要，请稍候...")
        summary = summarizer.summarize(transcript, style="bullet")
        
        # 保存摘要到桌面
        summary_filename = f"{file_identifier}_summary.txt"
        summary_path = os.path.join(desktop, summary_filename)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"视频链接: {video_link}\n")
            f.write(f"BV号: {bv_number}\n")
            f.write("=" * 50 + "\n")
            f.write("【视频摘要】\n\n")
            f.write(summary)
            f.write("\n\n" + "=" * 50 + "\n")
            f.write("【完整文案】\n\n")
            f.write(transcript)
        
        print(f"摘要生成完成！已保存至: {summary_path}")
        print("\n" + "=" * 50)
        print("【摘要内容】")
        print(summary)
        
    except Exception as e:
        print(f"生成摘要时出错: {e}")
        print("转录文本已保存，可以手动使用其他工具生成摘要")
    
    print("\n" + "=" * 50)
    print("处理完成！")
    print(f"转录文件: {output_path}")
    if os.path.exists(summary_path):
        print(f"摘要文件: {summary_path}")

if __name__ == "__main__":
    main()
