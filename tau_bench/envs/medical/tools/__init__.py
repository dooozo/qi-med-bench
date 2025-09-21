# Copyright Sierra

import json
import os
from typing import List, Dict, Any
from .medical_tools import *

def get_medical_tools() -> List[Dict[str, Any]]:
    """获取所有医疗工具的定义"""
    
    # 加载工具定义
    tools_file = os.path.join(os.path.dirname(__file__), "../../../../qi_med_tools.json")
    with open(tools_file, 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    
    # 工具函数映射
    tool_functions = {
        "get_chest_ct_metrics": get_chest_ct_metrics,
        "get_tumor_markers": get_tumor_markers,
        "get_pathology_data": get_pathology_data,
        "get_genetic_mutations": get_genetic_mutations,
        "get_pdl1_expression": get_pdl1_expression,
        "get_tnm_staging_details": get_tnm_staging_details,
        "get_performance_status": get_performance_status,
        "get_pulmonary_function": get_pulmonary_function,
        "get_blood_routine": get_blood_routine,
        "get_liver_kidney_function": get_liver_kidney_function,
        "get_treatment_history": get_treatment_history,
        "get_immune_adverse_events": get_immune_adverse_events,
        "get_chemo_toxicity": get_chemo_toxicity,
        "get_radiation_parameters": get_radiation_parameters,
        "get_surgery_feasibility": get_surgery_feasibility,
    }
    
    # 转换为tau_bench格式
    tools_info = []
    for tool in tools_data['tools']:
        tool_name = tool['tool_name']
        if tool_name in tool_functions:
            tool_info = {
                "name": tool_name,
                "description": tool['tool_description'],
                "parameters": tool['parameters'],
                "function": tool_functions[tool_name]
            }
            tools_info.append(tool_info)
    
    return tools_info