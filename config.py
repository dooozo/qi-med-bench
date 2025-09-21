"""
统一配置管理 - QI-Med-Bench 项目配置中心
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os

@dataclass
class Config:
    """统一配置管理类"""
    
    # === API 配置 ===
    api_key: str = "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"
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemini-2.5-pro"
    
    # === 项目路径配置 ===
    root_dir: Path = Path(__file__).parent
    data_dir: Path = root_dir / "data"
    output_dir: Path = root_dir / "output"
    
    # === 数据文件路径 ===
    @property
    def patients_file(self) -> Path:
        return self.root_dir / "data.json"
    
    @property 
    def eval_file(self) -> Path:
        return self.root_dir / "eval_dataset.json"
        
    @property
    def tools_file(self) -> Path:
        return self.root_dir / "qi_med_tools.json"
        
    @property
    def queries_file(self) -> Path:
        return self.root_dir / "initial_queries.json"
    
    # === 输出路径 ===
    @property
    def db_dir(self) -> Path:
        return self.root_dir / "medical_databases"
        
    @property
    def cases_dir(self) -> Path:
        return self.root_dir / "patient_cases"
        
    @property
    def results_dir(self) -> Path:
        return self.root_dir / "evaluation_results"
    
    # === 多线程配置 ===
    max_workers: int = 8
    max_retries: int = 5
    timeout: int = 300
    base_delay: float = 0.2
    
    # === 速率限制配置 ===
    requests_per_minute: int = 200
    batch_size: int = 10
    
    # === 评测配置 ===
    max_turns: int = 10
    temperature: float = 0.3
    
    # === 数据集大小 ===
    total_patients: int = 86
    total_tools: int = 15
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保所有目录存在
        self.data_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.db_dir.mkdir(exist_ok=True) 
        self.cases_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        
        # 从环境变量覆盖配置
        if api_key := os.getenv("OPENROUTER_API_KEY"):
            self.api_key = api_key
        if model := os.getenv("OPENROUTER_MODEL"):
            self.model = model
    
    def get_db_file(self, tool_id: str, tool_name: str) -> Path:
        """获取工具数据库文件路径"""
        return self.db_dir / f"{tool_id}_{tool_name}_database.json"
    
    def get_case_file(self, patient_id: str) -> Path:
        """获取患者案例文件路径"""
        return self.cases_dir / f"patient_{patient_id}.json"

# 全局配置实例
config = Config()