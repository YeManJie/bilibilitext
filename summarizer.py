"""
视频摘要模块 - 基于Ollama本地LLM实现智能摘要功能
"""
import ollama
from typing import Iterator, Optional, Callable
import threading


class VideoSummarizer:
    """视频摘要生成器，支持Ollama本地模型"""
    
    def __init__(self, model: str = "qwen2.5:7b", host: str = "http://localhost:11434"):
        """
        初始化摘要生成器
        
        Args:
            model: Ollama模型名称，默认使用qwen2.5:7b
            host: Ollama服务器地址
        """
        self.host = host
        self.model = model
        self.client = None
        self._is_available = False
        self._lock = threading.Lock()
        self._connect()
    
    def _connect(self):
        """尝试连接Ollama服务"""
        try:
            self.client = ollama.Client(host=self.host)
            # 测试连接
            self.client.list()
            self._is_available = True
        except Exception as e:
            self._is_available = False
            print(f"[WARNING] 无法连接到Ollama服务: {e}")
    
    def is_available(self) -> bool:
        """检查Ollama服务是否可用"""
        return self._is_available
    
    def check_model_exists(self) -> bool:
        """检查配置的模型是否存在"""
        if not self._is_available:
            return False
        try:
            models = self.client.list()
            # 处理不同版本的Ollama API返回格式
            model_list = models.get('models', [])
            model_names = []
            for m in model_list:
                # 新版API使用'model'字段，旧版使用'name'字段
                name = m.get('model') or m.get('name', '')
                model_names.append(name)
            # 支持带和不带tag的匹配
            return any(self.model in name or name in self.model for name in model_names)
        except Exception as e:
            print(f"[ERROR] 检查模型时出错: {e}")
            return False
    
    def summarize(self, text: str, style: str = "bullet", 
                  on_chunk: Optional[Callable[[str], None]] = None) -> str:
        """
        生成视频摘要
        
        Args:
            text: 视频转录文本
            style: 摘要风格 - bullet(要点) | narrative(叙述) | detailed(详细)
            on_chunk: 流式回调函数，每生成一个chunk会调用
            
        Returns:
            完整摘要文本
        """
        if not self._is_available:
            raise RuntimeError("Ollama服务不可用，请确保Ollama已启动")
        
        if not text or not text.strip():
            return "输入文本为空，无法生成摘要"
        
        # 处理长文本 - 分割并递归摘要
        max_input_length = 8000
        if len(text) > max_input_length:
            return self._summarize_long_text(text, style, on_chunk)
        
        prompt = self._build_prompt(text, style)
        
        try:
            full_response = []
            stream = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            
            for chunk in stream:
                content = chunk['message']['content']
                full_response.append(content)
                if on_chunk:
                    on_chunk(content)
            
            return ''.join(full_response)
        except Exception as e:
            error_msg = f"生成摘要时出错: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg
    
    def _summarize_long_text(self, text: str, style: str, 
                             on_chunk: Optional[Callable[[str], None]]) -> str:
        """处理长文本 - 分块摘要后合并"""
        chunk_size = 8000
        overlap = 200  # 重叠部分，保持上下文
        
        # 分割文本
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            # 尽量在句子边界分割
            if end < len(text):
                # 寻找最近的句号
                for i in range(end, start + chunk_size // 2, -1):
                    if i < len(text) and text[i] in '。！？\n':
                        end = i + 1
                        break
            chunks.append(text[start:end])
            start = end - overlap
        
        print(f"[INFO] 文本较长({len(text)}字)，分为{len(chunks)}段处理")
        
        # 分别摘要每个块
        partial_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"[INFO] 正在处理第{i+1}/{len(chunks)}段...")
            prompt = self._build_prompt(chunk, style)
            
            try:
                response = self.client.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False
                )
                partial_summaries.append(response['message']['content'])
            except Exception as e:
                print(f"[ERROR] 处理第{i+1}段时出错: {e}")
                partial_summaries.append(f"[第{i+1}段处理失败]")
        
        # 合并部分摘要
        if len(partial_summaries) == 1:
            return partial_summaries[0]
        
        # 对合并后的摘要再次进行摘要
        combined = "\n\n".join(partial_summaries)
        if len(combined) > chunk_size:
            print("[WARNING] 合并后文本仍过长，直接返回分段摘要")
            return combined
        
        print("[INFO] 正在合并各段摘要...")
        final_prompt = f"""请将以下各段摘要整合成一份完整的视频摘要：

{combined}

要求：
1. 去除重复内容
2. 保持逻辑连贯
3. 使用{self._get_style_name(style)}形式呈现
"""
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": final_prompt}],
                stream=True
            )
            
            full_response = []
            for chunk in response:
                content = chunk['message']['content']
                full_response.append(content)
                if on_chunk:
                    on_chunk(content)
            
            return ''.join(full_response)
        except Exception as e:
            print(f"[ERROR] 合并摘要时出错: {e}")
            return combined  # 回退到简单合并
    
    def _build_prompt(self, text: str, style: str) -> str:
        """构建提示词"""
        templates = {
            "bullet": """请为以下视频内容生成摘要，使用要点形式列出关键信息：

要求：
1. 提炼3-7个核心要点
2. 每个要点简明扼要
3. 使用中文
4. 保留关键数据和事实

视频内容：
{text}""",
            "narrative": """请用一段话总结以下视频的核心内容：

要求：
1. 控制在200-300字
2. 突出主题和核心观点
3. 语言流畅自然
4. 使用中文

视频内容：
{text}""",
            "detailed": """请详细总结以下视频内容：

要求：
1. 分段介绍视频结构（开头、主体、结尾）
2. 列出主要观点和关键数据
3. 说明视频的核心价值或启示
4. 使用中文，可适当使用列表

视频内容：
{text}"""
        }
        
        template = templates.get(style, templates["bullet"])
        return template.format(text=text[:8000])  # 限制输入长度
    
    def _get_style_name(self, style: str) -> str:
        """获取风格的中文名称"""
        names = {
            "bullet": "要点列表",
            "narrative": "叙述",
            "detailed": "详细"
        }
        return names.get(style, "要点")


class SummaryConfig:
    """摘要配置管理"""
    
    DEFAULT_MODEL = "qwen2.5:7b"
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_STYLE = "bullet"
    
    STYLES = {
        "bullet": "要点形式",
        "narrative": "叙述形式", 
        "detailed": "详细形式"
    }
    
    @classmethod
    def get_available_models(cls) -> list:
        """获取可用的Ollama模型列表"""
        try:
            client = ollama.Client(host=cls.DEFAULT_HOST)
            models = client.list()
            return [m['name'] for m in models.get('models', [])]
        except:
            return []


def create_summarizer(host: str = None, model: str = None) -> VideoSummarizer:
    """
    工厂函数，创建摘要生成器实例
    
    Args:
        host: Ollama服务器地址，默认使用配置值
        model: 模型名称，默认使用配置值
        
    Returns:
        VideoSummarizer实例
    """
    return VideoSummarizer(
        model=model or SummaryConfig.DEFAULT_MODEL,
        host=host or SummaryConfig.DEFAULT_HOST
    )


if __name__ == "__main__":
    # 测试代码
    print("测试视频摘要模块...")
    
    summarizer = create_summarizer()
    
    if not summarizer.is_available():
        print("Ollama服务不可用，请确保Ollama已启动")
        exit(1)
    
    print(f"Ollama服务可用，模型: {summarizer.model}")
    print(f"模型已安装: {summarizer.check_model_exists()}")
    
    # 测试文本
    test_text = """
    这是一段测试文本，模拟视频转录内容。
    主要介绍了人工智能的发展历程，从早期的专家系统到现代的深度学习。
    重点讨论了Transformer架构对自然语言处理的革命性影响。
    """
    
    print("\n生成要点形式摘要：")
    print("=" * 50)
    
    def on_chunk(chunk):
        print(chunk, end='', flush=True)
    
    result = summarizer.summarize(test_text, style="bullet", on_chunk=on_chunk)
    print("\n" + "=" * 50)
    print("摘要完成！")
