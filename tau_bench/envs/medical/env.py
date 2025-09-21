# Copyright Sierra

import json
import os
from typing import Dict, List, Any, Optional, Union
from tau_bench.envs.base import Env
from tau_bench.envs.user import UserStrategy
from tau_bench.envs.medical.tools import get_medical_tools
from tau_bench.envs.medical.tasks import get_medical_tasks


class QIMedicalDomainEnv(Env):
    """QI医学领域环境，专注于肺癌三期的多轮工具调用评测"""
    
    def __init__(
        self,
        user_strategy: Union[str, UserStrategy],
        user_model: str,
        task_split: str = "test",
        user_provider: Optional[str] = None,
        task_index: Optional[int] = None,
    ):
        # 加载医疗工具
        tools_info = get_medical_tools()
        
        # 加载医疗任务
        tasks = get_medical_tasks(task_split)
        
        # 医疗领域的wiki信息
        wiki = """
QI-Med-Bench 肺癌三期多轮工具调用评测系统

## 系统概述
本系统专门评测AI模型在肺癌三期诊疗场景中的多轮工具调用能力。系统提供15个专业医疗工具，涵盖：
- 影像学检查：胸部CT指标
- 实验室检验：肿瘤标志物、血常规、肝肾功能  
- 病理检查：病理数据、基因突变、PD-L1表达
- 分期评估：TNM分期详情
- 功能评估：体能状态、肺功能
- 治疗相关：治疗史、毒副反应、放疗参数、手术可行性

## 工具使用原则
1. 工具返回纯客观数据，不提供医学建议
2. 模型需基于工具返回的原始数据进行医学推理
3. 鼓励多轮、按需调用工具获取完整信息
4. 最终生成综合性的诊疗建议

## 评测标准
- 工具调用的合理性和完整性
- 基于工具数据的医学推理能力
- 最终诊疗建议的准确性和可行性
"""
        
        super().__init__(
            tools_info=tools_info,
            tasks=tasks,
            wiki=wiki,
            user_strategy=user_strategy,
            user_model=user_model,
            user_provider=user_provider,
            task_index=task_index,
        )