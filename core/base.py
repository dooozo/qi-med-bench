"""
基础类定义 - 消除重复代码
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional
from threading import Lock
from openai import OpenAI

from config import Config

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """错误类型枚举"""
    API_ERROR = "API调用失败"
    DATA_ERROR = "数据格式错误"
    TOOL_ERROR = "工具执行失败"
    FILE_ERROR = "文件操作失败"
    VALIDATION_ERROR = "数据验证失败"

class MedicalBenchError(Exception):
    """自定义异常类"""
    
    def __init__(self, error_type: ErrorType, message: str, context: Dict = None):
        self.error_type = error_type
        self.context = context or {}
        super().__init__(f"{error_type.value}: {message}")

class ThreadSafeAPIClient:
    """线程安全的API客户端"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        self.lock = Lock()
        self.request_times = []
        
    def call_api(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """线程安全的API调用"""
        self._rate_limit()
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    timeout=self.config.timeout,
                    **kwargs
                )
                
                if response.choices:
                    return response.choices[0].message.content or ""
                else:
                    raise MedicalBenchError(
                        ErrorType.API_ERROR, 
                        "API返回空响应",
                        {"attempt": attempt + 1}
                    )
                    
            except Exception as e:
                wait_time = self.config.base_delay * (2 ** attempt)
                logger.warning(f"第{attempt + 1}次API调用失败: {str(e)[:100]}...")
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    raise MedicalBenchError(
                        ErrorType.API_ERROR,
                        f"所有{self.config.max_retries}次尝试均失败: {str(e)}",
                        {"final_error": str(e)}
                    )
        
        return ""
    
    def _rate_limit(self) -> None:
        """速率限制控制"""
        with self.lock:
            now = time.time()
            # 清理60秒前的请求记录
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            # 如果请求过于频繁，等待
            if len(self.request_times) >= self.config.requests_per_minute:
                sleep_time = 60 - (now - self.request_times[0])
                if sleep_time > 0:
                    logger.info(f"速率限制: 等待{sleep_time:.1f}秒")
                    time.sleep(sleep_time)
            
            self.request_times.append(now)

class BaseGenerator(ABC):
    """生成器基类"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_client = ThreadSafeAPIClient(config)
        self.stats = {
            'total_processed': 0,
            'total_failed': 0,
            'start_time': None
        }
        self.stats_lock = Lock()
        
    def update_stats(self, processed: int = 0, failed: int = 0) -> None:
        """更新统计信息"""
        with self.stats_lock:
            self.stats['total_processed'] += processed
            self.stats['total_failed'] += failed
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.stats_lock:
            elapsed = time.time() - (self.stats['start_time'] or time.time())
            return {
                **self.stats,
                'elapsed_time': elapsed,
                'success_rate': (
                    self.stats['total_processed'] / 
                    (self.stats['total_processed'] + self.stats['total_failed'])
                    if (self.stats['total_processed'] + self.stats['total_failed']) > 0
                    else 0
                ),
                'requests_per_second': self.stats['total_processed'] / elapsed if elapsed > 0 else 0
            }
    
    def save_json(self, data: Any, file_path: str, **kwargs) -> None:
        """保存JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, **kwargs)
            logger.info(f"✅ 已保存: {file_path}")
        except Exception as e:
            raise MedicalBenchError(
                ErrorType.FILE_ERROR,
                f"保存文件失败: {file_path}",
                {"error": str(e)}
            )
    
    def load_json(self, file_path: str) -> Any:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise MedicalBenchError(
                ErrorType.FILE_ERROR,
                f"文件不存在: {file_path}"
            )
        except json.JSONDecodeError as e:
            raise MedicalBenchError(
                ErrorType.DATA_ERROR,
                f"JSON解析失败: {file_path}",
                {"error": str(e)}
            )
    
    def parse_json_response(self, response: str, context: str = "") -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败 - {context}: {str(e)}")
            # 尝试从响应中提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # 如果完全无法解析，返回包装的结果
            return {
                "status": "parsing_failed",
                "raw_response": response[:500],
                "error": str(e),
                "context": context
            }
    
    @abstractmethod
    def generate(self) -> Any:
        """子类必须实现的生成方法"""
        pass
    
    def run(self) -> Any:
        """运行生成器"""
        logger.info(f"🚀 启动{self.__class__.__name__}")
        self.stats['start_time'] = time.time()
        
        try:
            result = self.generate()
            
            stats = self.get_stats()
            logger.info(f"✅ 生成完成: 成功{stats['total_processed']}, 失败{stats['total_failed']}")
            logger.info(f"⏱️ 用时{stats['elapsed_time']:.1f}s, 速率{stats['requests_per_second']:.2f}/s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 生成失败: {str(e)}")
            raise