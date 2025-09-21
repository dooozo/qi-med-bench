# Copyright Sierra

import json
import os
from typing import List, Dict, Any


def get_medical_tasks(task_split: str = "test") -> List[Dict[str, Any]]:
    """获取医疗任务数据"""
    
    # 任务数据文件路径
    if task_split == "test":
        # 首先尝试使用生成的初始queries
        initial_queries_file = os.path.join(os.path.dirname(__file__), "../../../initial_queries.json")
        if os.path.exists(initial_queries_file):
            with open(initial_queries_file, 'r', encoding='utf-8') as f:
                queries_data = json.load(f)
            
            # 转换为任务格式
            tasks = []
            for query_data in queries_data:
                task = {
                    "user_id": query_data["patient_id"],
                    "instruction": query_data["initial_query"],
                    "actions": [],  # 会在环境中动态填充
                    "outputs": [],  # 会在环境中动态填充
                    "metadata": query_data["metadata"]
                }
                tasks.append(task)
            return tasks
        
        # 如果初始queries还没生成完，使用eval_dataset作为备选
        eval_dataset_file = os.path.join(os.path.dirname(__file__), "../../../eval_dataset.json")
        if os.path.exists(eval_dataset_file):
            with open(eval_dataset_file, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)
            
            # 转换为任务格式
            tasks = []
            for item in eval_data:
                task = {
                    "user_id": item["id"],
                    "instruction": item["query"],
                    "actions": [],
                    "outputs": [],
                    "metadata": item.get("metadata", {})
                }
                tasks.append(task)
            return tasks
    
    # 如果没有找到数据文件，返回空列表
    print(f"Warning: No task data found for split '{task_split}'")
    return []