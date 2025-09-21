# Copyright Sierra

import json
import os
from typing import Dict, Any, Optional


class MedicalDatabaseManager:
    """医疗数据库管理器，负责从生成的数据库中获取患者数据"""
    
    def __init__(self):
        self.databases = {}
        self.database_dir = os.path.join(os.path.dirname(__file__), "../../../../medical_databases")
        self._load_databases()
    
    def _load_databases(self):
        """加载所有医疗数据库"""
        if not os.path.exists(self.database_dir):
            print(f"Warning: Database directory {self.database_dir} not found")
            return
        
        # 加载数据库索引
        index_file = os.path.join(self.database_dir, "database_index.json")
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 加载每个工具的数据库
            for db_file in index_data.get('database_files', []):
                db_path = os.path.join(self.database_dir, db_file)
                if os.path.exists(db_path):
                    tool_id = db_file.split('_')[0]  # 提取工具ID
                    with open(db_path, 'r', encoding='utf-8') as f:
                        self.databases[tool_id] = json.load(f)
    
    def get_tool_data(self, tool_id: str, patient_id: str) -> Dict[str, Any]:
        """获取指定患者的指定工具数据"""
        if tool_id in self.databases and patient_id in self.databases[tool_id]:
            return self.databases[tool_id][patient_id]
        else:
            # 如果没有找到数据，返回空结果或默认值
            return {"error": f"No data found for patient {patient_id} with tool {tool_id}"}


# 全局数据库管理器实例
db_manager = MedicalDatabaseManager()


# 工具函数实现
def get_chest_ct_metrics(patient_id: str, scan_date: Optional[str] = None) -> Dict[str, Any]:
    """获取胸部CT影像学客观指标数据，包括肿瘤尺寸、位置、淋巴结状态等原始测量值"""
    return db_manager.get_tool_data("LC001", patient_id)


def get_tumor_markers(patient_id: str, test_date: Optional[str] = None) -> Dict[str, Any]:
    """查询肺癌相关肿瘤标志物的实验室数值"""
    return db_manager.get_tool_data("LC002", patient_id)


def get_pathology_data(patient_id: str, specimen_id: Optional[str] = None) -> Dict[str, Any]:
    """获取病理学检查的原始数据，包括组织学类型、分化程度等客观病理指标"""
    return db_manager.get_tool_data("LC003", patient_id)


def get_genetic_mutations(patient_id: str, test_type: Optional[str] = None) -> Dict[str, Any]:
    """查询基因突变检测结果，返回突变类型和丰度等原始数据"""
    return db_manager.get_tool_data("LC004", patient_id)


def get_pdl1_expression(patient_id: str, antibody_clone: Optional[str] = None) -> Dict[str, Any]:
    """获取PD-L1免疫组化表达水平的定量数据"""
    return db_manager.get_tool_data("LC005", patient_id)


def get_tnm_staging_details(patient_id: str) -> Dict[str, Any]:
    """获取TNM分期的详细测量数据和评估指标"""
    return db_manager.get_tool_data("LC006", patient_id)


def get_performance_status(patient_id: str, assessment_date: Optional[str] = None) -> Dict[str, Any]:
    """查询患者体能状态评分和相关生理指标"""
    return db_manager.get_tool_data("LC007", patient_id)


def get_pulmonary_function(patient_id: str) -> Dict[str, Any]:
    """获取肺功能检查的客观测量值"""
    return db_manager.get_tool_data("LC008", patient_id)


def get_blood_routine(patient_id: str, test_date: Optional[str] = None) -> Dict[str, Any]:
    """查询血常规检验的原始数值"""
    return db_manager.get_tool_data("LC009", patient_id)


def get_liver_kidney_function(patient_id: str) -> Dict[str, Any]:
    """获取肝肾功能的实验室检查数值"""
    return db_manager.get_tool_data("LC010", patient_id)


def get_treatment_history(patient_id: str, treatment_type: Optional[str] = None) -> Dict[str, Any]:
    """查询既往治疗的详细参数和时间线"""
    return db_manager.get_tool_data("LC011", patient_id)


def get_immune_adverse_events(patient_id: str) -> Dict[str, Any]:
    """获取免疫治疗相关不良反应的分级数据"""
    return db_manager.get_tool_data("LC012", patient_id)


def get_chemo_toxicity(patient_id: str, chemotherapy_regimen: Optional[str] = None) -> Dict[str, Any]:
    """查询化疗相关毒副反应的定量指标"""
    return db_manager.get_tool_data("LC013", patient_id)


def get_radiation_parameters(patient_id: str) -> Dict[str, Any]:
    """获取放疗的物理剂量参数"""
    return db_manager.get_tool_data("LC014", patient_id)


def get_surgery_feasibility(patient_id: str) -> Dict[str, Any]:
    """评估手术可行性的客观指标"""
    return db_manager.get_tool_data("LC015", patient_id)