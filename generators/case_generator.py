"""患者案例生成器"""
from typing import Dict, List, Any
from core.base import BaseGenerator
from config import Config

class PatientCaseGenerator(BaseGenerator):
    def generate(self) -> List[Dict]:
        """生成患者案例（简化版本）"""
        return []