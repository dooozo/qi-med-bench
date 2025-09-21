"""
数据管理器 - 统一数据加载和处理
"""

import os
from typing import Dict, List, Any, Tuple
from pathlib import Path

from .base import BaseGenerator, MedicalBenchError, ErrorType
from config import Config

class DataManager:
    """统一数据管理器"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def load_patients_data(self) -> List[Dict[str, Any]]:
        """加载患者数据"""
        try:
            with open(self.config.patients_file, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
            return data
        except Exception as e:
            raise MedicalBenchError(
                ErrorType.FILE_ERROR,
                f"加载患者数据失败: {self.config.patients_file}",
                {"error": str(e)}
            )
    
    def load_eval_data(self) -> List[Dict[str, Any]]:
        """加载评测数据"""
        try:
            with open(self.config.eval_file, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
            return data
        except Exception as e:
            raise MedicalBenchError(
                ErrorType.FILE_ERROR,
                f"加载评测数据失败: {self.config.eval_file}",
                {"error": str(e)}
            )
    
    def load_tools_data(self) -> List[Dict[str, Any]]:
        """加载工具数据"""
        try:
            with open(self.config.tools_file, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
            return data.get('tools', [])
        except Exception as e:
            raise MedicalBenchError(
                ErrorType.FILE_ERROR,
                f"加载工具数据失败: {self.config.tools_file}",
                {"error": str(e)}
            )
    
    def load_initial_queries(self) -> Dict[str, Dict[str, Any]]:
        """加载初始查询数据"""
        if not self.config.queries_file.exists():
            return {}
        
        try:
            with open(self.config.queries_file, 'r', encoding='utf-8') as f:
                import json
                queries_list = json.load(f)
            
            # 转换为字典格式
            return {query['patient_id']: query for query in queries_list}
        except Exception as e:
            raise MedicalBenchError(
                ErrorType.FILE_ERROR,
                f"加载初始查询失败: {self.config.queries_file}",
                {"error": str(e)}
            )
    
    def load_all_data(self) -> Tuple[List[Dict], List[Dict], Dict[str, Dict], List[Dict]]:
        """加载所有数据"""
        patients_data = self.load_patients_data()
        eval_data = self.load_eval_data()
        initial_queries = self.load_initial_queries()
        tools_data = self.load_tools_data()
        
        return patients_data, eval_data, initial_queries, tools_data
    
    def load_medical_databases(self) -> Dict[str, Dict[str, Any]]:
        """加载医疗数据库"""
        databases = {}
        
        if not self.config.db_dir.exists():
            return databases
        
        # 加载索引文件
        index_file = self.config.db_dir / "database_index.json"
        if not index_file.exists():
            return databases
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                import json
                index_data = json.load(f)
            
            # 加载各个数据库文件
            for db_file in index_data.get('database_files', []):
                db_path = self.config.db_dir / db_file
                if db_path.exists():
                    tool_id = db_file.split('_')[0]
                    with open(db_path, 'r', encoding='utf-8') as f:
                        databases[tool_id] = json.load(f)
            
            return databases
            
        except Exception as e:
            raise MedicalBenchError(
                ErrorType.FILE_ERROR,
                f"加载医疗数据库失败: {index_file}",
                {"error": str(e)}
            )
    
    def save_database_index(self, tools: List[Dict], patients: List[Dict], 
                           generation_stats: Dict = None) -> None:
        """保存数据库索引"""
        index_data = {
            "tools": [{"tool_id": tool['tool_id'], "tool_name": tool['tool_name']} 
                     for tool in tools],
            "patients": [str(p['id']) for p in patients],
            "database_files": [f"{tool['tool_id']}_{tool['tool_name']}_database.json" 
                              for tool in tools],
            "generation_stats": generation_stats or {}
        }
        
        index_file = self.config.db_dir / "database_index.json"
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(index_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise MedicalBenchError(
                ErrorType.FILE_ERROR,
                f"保存数据库索引失败: {index_file}",
                {"error": str(e)}
            )