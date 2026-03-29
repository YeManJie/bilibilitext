import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import webbrowser
import re
import sys
import threading
import os
from utils import download_video
from exAudio import convert_flv_to_mp3, split_mp3, process_audio_split

speech_to_text = None
summarizer = None
last_output_path = None

def is_cuda_available(whisper):
    return whisper.torch.cuda.is_available()

def open_popup(text, title="提示"):
    popup = ttk.Toplevel()
    popup.title(title)
    popup.geometry("300x150")
    popup.update_idletasks()
    x = (popup.winfo_screenwidth() - popup.winfo_reqwidth()) // 2
    y = (popup.winfo_screenheight() - popup.winfo_reqheight()) // 2
    popup.geometry("+%d+%d" % (x, y))
    label = ttk.Label(popup, text=text)
    label.pack(pady=10)
    user_choice = ttk.StringVar()

    def on_confirm():
        user_choice.set("confirmed")
        popup.destroy()
    confirm_button = ttk.Button(popup, text="确定", style="primary.TButton", command=on_confirm)
    confirm_button.pack(side=LEFT, padx=10, pady=10)

    def on_cancel():
        user_choice.set("cancelled")
        popup.destroy()
    cancel_button = ttk.Button(popup, text="取消", style="outline-danger.TButton", command=on_cancel)
    cancel_button.pack(side=RIGHT, padx=10, pady=10)
    popup.wait_window()
    return user_choice.get()

def show_log(text, state="INFO"):
    log_text.config(state="normal")
    log_text.insert(END, "[LOG][{}] {}\n".format(state, text))
    log_text.config(state="disabled")
    log_text.see(END)

def on_submit_click():
    global speech_to_text, last_output_path
    if speech_to_text is None:
        print("Whisper未加载！请点击加载Whisper按钮。")
        return
    video_link = video_link_entry.get()
    if not video_link:
        print("视频链接不能为空！")
        return
    if open_popup("是否确定生成？可能耗费时间较长", title="提示") == "cancelled":
        return
    pattern = r'BV[A-Za-z0-9]+'
    matches = re.findall(pattern, video_link)
    if not matches:
        print("无效的视频链接！")
        return
    bv_number = matches[0]
    print("视频链接: {}, BV号: {}".format(video_link, bv_number))
    thread = threading.Thread(target=process_video, args=(bv_number[2:],))
    thread.start()

def process_video(av_number):
    global last_output_path
    print("=" * 10)
    print("正在下载视频...")
    file_identifier = download_video(str(av_number))
    print("=" * 10)
    print("正在分割音频...")
    folder_name = process_audio_split(file_identifier)
    print("=" * 10)
    print("正在转换文本（可能耗时较长）...")
    speech_to_text.run_analysis(folder_name, 
        prompt="以下是普通话的句子。这是一个关于{}的视频。".format(file_identifier))
    last_output_path = "outputs/{}.txt".format(folder_name)
    print("转换完成！{}".format(last_output_path))
    
    def ask_for_summary():
        if summarizer and summarizer.is_available():
            popup = ttk.Toplevel()
            popup.title("生成摘要")
            popup.geometry("350x150")
            popup.update_idletasks()
            x = (popup.winfo_screenwidth() - popup.winfo_reqwidth()) // 2
            y = (popup.winfo_screenheight() - popup.winfo_reqheight()) // 2
            popup.geometry("+%d+%d" % (x, y))
            
            ttk.Label(popup, text="视频转录完成！是否生成摘要？", font=("Helvetica", 12)).pack(pady=15)
            
            btn_frame = ttk.Frame(popup)
            btn_frame.pack(pady=10)
            
            def yes_callback():
                popup.destroy()
                on_generate_summary_click()
            
            def no_callback():
                popup.destroy()
            
            ttk.Button(btn_frame, text="生成摘要", command=yes_callback, bootstyle="success", width=10).pack(side=LEFT, padx=10)
            ttk.Button(btn_frame, text="稍后生成", command=no_callback, bootstyle="outline", width=10).pack(side=LEFT, padx=10)
    
    video_link_entry.after(500, ask_for_summary)

def on_generate_again_click():
    print("再次生成...")
    print(open_popup("是否再次生成？"))

def on_clear_log_click():
    try:
        sys.stdout = _orig_stdout
        sys.stderr = _orig_stderr
    except NameError:
        pass
    try:
        log_text.config(state="normal")
        log_text.delete('1.0', END)
        log_text.config(state="disabled")
    finally:
        try:
            redirect_system_io()
        except Exception:
            pass

def on_show_result_click():
    global last_output_path
    if last_output_path and os.path.exists(last_output_path):
        with open(last_output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        popup = ttk.Toplevel()
        popup.title("转录结果")
        popup.geometry("600x500")
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - popup.winfo_reqwidth()) // 2
        y = (popup.winfo_screenheight() - popup.winfo_reqheight()) // 2
        popup.geometry("+%d+%d" % (x, y))
        
        text_widget = ttk.ScrolledText(popup, wrap="word")
        text_widget.pack(padx=10, pady=10, fill=BOTH, expand=YES)
        text_widget.insert(END, content)
        text_widget.config(state="disabled")
    else:
        print("暂无转录结果")

def on_select_model():
    selected_model = model_var.get()
    print("选中的模型: {}".format(selected_model))
    print("请点击加载Whisper按钮加载模型！")

def on_confirm_model_click():
    selected_model = model_var.get()
    print("确认的模型: {}".format(selected_model))
    print("请点击加载Whisper按钮加载模型！")

def load_whisper_model():
    global speech_to_text
    import speech2text
    speech_to_text = speech2text
    speech_to_text.load_whisper(model=model_var.get())
    msg = "CUDA加速已启用" if is_cuda_available(speech_to_text.whisper) else "使用CPU计算"
    print("加载Whisper成功！", msg)

def load_ollama_model():
    global summarizer
    try:
        from summarizer import create_summarizer
        model_name = summary_model_var.get() or "qwen2.5:7b"
        summarizer = create_summarizer(model=model_name)
        if summarizer.is_available():
            print("Ollama服务已连接，模型: {}".format(model_name))
            if summarizer.check_model_exists():
                print("模型 {} 已就绪".format(model_name))
            else:
                print("[WARNING] 模型 {} 未找到，请先执行: ollama pull {}".format(model_name, model_name))
        else:
            print("[WARNING] 无法连接到Ollama服务，请确保Ollama已启动")
    except Exception as e:
        print("[ERROR] 加载Ollama模型失败: {}".format(e))

def on_generate_summary_click():
    global summarizer, last_output_path
    
    text_content = ""
    if last_output_path and os.path.exists(last_output_path):
        with open(last_output_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
    
    if not text_content:
        outputs_dir = "outputs"
        if os.path.exists(outputs_dir):
            txt_files = [f for f in os.listdir(outputs_dir) if f.endswith('.txt')]
            if txt_files:
                txt_files.sort(key=lambda x: os.path.getmtime(os.path.join(outputs_dir, x)), reverse=True)
                latest_file = os.path.join(outputs_dir, txt_files[0])
                with open(latest_file, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                last_output_path = latest_file
    
    if not text_content:
        print("[ERROR] 没有找到转录文本，请先完成视频转录")
        return
    
    if summarizer is None:
        load_ollama_model()
    
    if not summarizer or not summarizer.is_available():
        print("[ERROR] Ollama服务不可用，无法生成摘要")
        return
    
    summary_window = ttk.Toplevel()
    summary_window.title("视频摘要生成")
    summary_window.geometry("700x600")
    summary_window.update_idletasks()
    x = (summary_window.winfo_screenwidth() - summary_window.winfo_reqwidth()) // 2
    y = (summary_window.winfo_screenheight() - summary_window.winfo_reqheight()) // 2
    summary_window.geometry("+%d+%d" % (x, y))
    
    config_frame = ttk.LabelFrame(summary_window, text="配置", padding=10)
    config_frame.pack(fill=X, padx=10, pady=5)
    
    style_frame = ttk.Frame(config_frame)
    style_frame.pack(fill=X, pady=5)
    ttk.Label(style_frame, text="摘要风格:").pack(side=LEFT, padx=(0, 10))
    style_var = ttk.StringVar(value="bullet")
    style_combo = ttk.Combobox(style_frame, textvariable=style_var, 
                                values=["bullet", "narrative", "detailed"], width=15, state="readonly")
    style_combo.pack(side=LEFT)
    style_labels = {"bullet": "要点形式", "narrative": "叙述形式", "detailed": "详细形式"}
    style_label = ttk.Label(style_frame, text=style_labels["bullet"], foreground="gray")
    style_label.pack(side=LEFT, padx=10)
    
    def on_style_change(event):
        style_label.config(text=style_labels.get(style_var.get(), ""))
    style_combo.bind("<<ComboboxSelected>>", on_style_change)
    
    btn_frame = ttk.Frame(config_frame)
    btn_frame.pack(fill=X, pady=5)
    
    generate_btn = ttk.Button(btn_frame, text="开始生成", bootstyle="success")
    generate_btn.pack(side=LEFT, padx=(0, 10))
    
    save_btn = ttk.Button(btn_frame, text="保存摘要", bootstyle="primary-outline", state="disabled")
    save_btn.pack(side=LEFT)
    
    progress_var = ttk.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(config_frame, variable=progress_var, maximum=100, mode="indeterminate")
    
    output_frame = ttk.LabelFrame(summary_window, text="摘要内容", padding=10)
    output_frame.pack(fill=BOTH, expand=YES, padx=10, pady=5)
    
    summary_text = ttk.ScrolledText(output_frame, wrap="word", state="disabled")
    summary_text.pack(fill=BOTH, expand=YES)
    
    status_label = ttk.Label(summary_window, text="就绪", foreground="gray", anchor=W)
    status_label.pack(fill=X, padx=10, pady=5)
    
    def update_text(text, append=True):
        summary_text.config(state="normal")
        if not append:
            summary_text.delete('1.0', END)
        summary_text.insert(END, text)
        summary_text.config(state="disabled")
        summary_text.see(END)
    
    def generate_summary():
        try:
            generate_btn.config(state="disabled")
            progress_bar.pack(fill=X, pady=5, after=btn_frame)
            progress_bar.start()
            status_label.config(text="正在生成摘要...", foreground="blue")
            
            summary_result = []
            
            def on_chunk(chunk):
                summary_result.append(chunk)
                summary_window.after(0, lambda: update_text(chunk, append=True))
            
            summary_window.after(0, lambda: update_text("", append=False))
            
            style = style_var.get()
            result = summarizer.summarize(text_content, style=style, on_chunk=on_chunk)
            
            if not summary_result:
                summary_window.after(0, lambda: update_text(result, append=False))
            
            status_label.config(text="摘要生成完成！", foreground="green")
            save_btn.config(state="normal")
            
        except Exception as e:
            status_label.config(text="生成失败: {}".format(str(e)), foreground="red")
            summary_window.after(0, lambda: update_text("\n\n[错误] {}".format(str(e)), append=True))
        finally:
            generate_btn.config(state="normal")
            progress_bar.stop()
            progress_bar.pack_forget()
    
    def save_summary():
        if last_output_path:
            base_path = last_output_path.replace('.txt', '_summary.txt')
        else:
            base_path = "outputs/summary.txt"
        
        summary_content = summary_text.get('1.0', END)
        with open(base_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        status_label.config(text="摘要已保存至: {}".format(base_path), foreground="green")
        print("摘要已保存至: {}".format(base_path))
    
    generate_btn.config(command=lambda: threading.Thread(target=generate_summary).start())
    save_btn.config(command=save_summary)

def open_github_link(event=None):
    webbrowser.open_new("https://github.com/lanbinshijie/bili2text")

def redirect_system_io():
    global _orig_stdout, _orig_stderr
    if '_orig_stdout' not in globals():
        _orig_stdout = sys.stdout
        _orig_stderr = sys.stderr

    class StdoutRedirector:
        def __init__(self):
            self._buffer = ""
        def write(self, message, state="INFO"):
            if not message:
                return
            if "Speed" in message:
                return
            self._buffer += message
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                if line.strip():
                    try:
                        log_text.config(state="normal")
                        log_text.insert(END, "[LOG][{}] {}\n".format(state, line))
                        log_text.config(state="disabled")
                        log_text.see(END)
                    except Exception:
                        try:
                            _orig_stdout.write(line + "\n")
                        except Exception:
                            pass
        def flush(self):
            if self._buffer.strip():
                try:
                    log_text.config(state="normal")
                    log_text.insert(END, "[LOG][INFO] {}\n".format(self._buffer))
                    log_text.config(state="disabled")
                    log_text.see(END)
                except Exception:
                    try:
                        _orig_stdout.write(self._buffer + "\n")
                    except Exception:
                        pass
            self._buffer = ""

    sys.stdout = StdoutRedirector()
    sys.stderr = StdoutRedirector()

def main():
    global video_link_entry, log_text, model_var, summary_model_var
    app = ttk.Window("Bili2Text - By Lanbin | www.lanbin.top", themename="litera")
    app.geometry("820x600")
    app.iconbitmap("favicon.ico")
    ttk.Label(app, text="Bilibili To Text", font=("Helvetica", 16)).pack(pady=10)
    
    video_link_frame = ttk.Frame(app)
    video_link_entry = ttk.Entry(video_link_frame)
    video_link_entry.pack(side=LEFT, expand=YES, fill=X)
    load_whisper_button = ttk.Button(video_link_frame, text="加载Whisper", command=load_whisper_model, bootstyle="success-outline")
    load_whisper_button.pack(side=RIGHT, padx=5)
    submit_button = ttk.Button(video_link_frame, text="下载视频", command=on_submit_click)
    submit_button.pack(side=RIGHT, padx=5)
    video_link_frame.pack(fill=X, padx=20)
    
    config_frame = ttk.LabelFrame(app, text="配置面板", padding=5)
    config_frame.pack(fill=X, padx=20, pady=5)
    
    whisper_frame = ttk.Frame(config_frame)
    whisper_frame.pack(fill=X, pady=2)
    ttk.Label(whisper_frame, text="Whisper模型:").pack(side=LEFT, padx=(0, 5))
    model_var = ttk.StringVar(value="small")
    model_combobox = ttk.Combobox(whisper_frame, textvariable=model_var, values=["tiny", "small", "medium", "large"], width=10)
    model_combobox.pack(side=LEFT)
    model_combobox.set("small")
    
    ollama_frame = ttk.Frame(config_frame)
    ollama_frame.pack(fill=X, pady=2)
    ttk.Label(ollama_frame, text="Ollama模型:").pack(side=LEFT, padx=(0, 5))
    summary_model_var = ttk.StringVar(value="qwen2.5:7b")
    summary_model_entry = ttk.Entry(ollama_frame, textvariable=summary_model_var, width=15)
    summary_model_entry.pack(side=LEFT, padx=(0, 10))
    load_ollama_btn = ttk.Button(ollama_frame, text="连接Ollama", command=load_ollama_model, bootstyle="info-outline")
    load_ollama_btn.pack(side=LEFT)
    
    log_text = ttk.ScrolledText(app, height=10, state="disabled")
    log_text.pack(padx=20, pady=10, fill=BOTH, expand=YES)
    
    controls_frame = ttk.Frame(app)
    controls_frame.pack(fill=X, padx=20)
    generate_button = ttk.Button(controls_frame, text="再次生成", command=on_generate_again_click)
    generate_button.pack(side=LEFT, padx=10, pady=10)
    show_result_button = ttk.Button(controls_frame, text="展示结果", command=on_show_result_click, bootstyle="success-outline")
    show_result_button.pack(side=LEFT, padx=10, pady=10)
    
    summary_button = ttk.Button(controls_frame, text="生成摘要", command=on_generate_summary_click, bootstyle="warning")
    summary_button.pack(side=LEFT, padx=10, pady=10)
    
    clear_log_button = ttk.Button(controls_frame, text="清空日志", command=on_clear_log_click, bootstyle=DANGER)
    clear_log_button.pack(side=LEFT, padx=10, pady=10)
    
    footer_frame = ttk.Frame(app)
    footer_frame.pack(side=BOTTOM, fill=X)
    author_label = ttk.Label(footer_frame, text="作者：Lanbin")
    author_label.pack(side=LEFT, padx=10, pady=10)
    version_var = ttk.StringVar(value="2.1.0")
    version_label = ttk.Label(footer_frame, text="版本 " + version_var.get(), foreground="gray")
    version_label.pack(side=LEFT, padx=10, pady=10)
    github_link = ttk.Label(footer_frame, text="开源仓库", cursor="hand2", bootstyle=PRIMARY)
    github_link.pack(side=LEFT, padx=10, pady=10)
    github_link.bind("<Button-1>", open_github_link)
    
    redirect_system_io()
    
    def delayed_ollama_connect():
        load_ollama_model()
    
    app.after(1000, delayed_ollama_connect)
    app.mainloop()

if __name__ == "__main__":
    main()
