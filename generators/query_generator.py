"""初始查询生成器"""
from typing import Dict, List, Any
from core.base import BaseGenerator
from config import Config

class QueryGenerator(BaseGenerator):
    def generate_queries(self, patients: List[Dict]) -> List[Dict]:
        """生成初始查询（简化版本）"""
        return [{"patient_id": str(p['id']), "initial_query": f"患者{p['gender']}，{p['age']}岁"} for p in patients]
    
    def generate(self) -> List[Dict]:
        return []