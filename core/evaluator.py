"""
QI-Med-Bench 评估器 - 重构版本
"""

import json
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .base import BaseGenerator, MedicalBenchError, ErrorType
from .data_manager import DataManager
from config import Config

class QIMedEvaluator(BaseGenerator):
    """医疗AI评估器"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.data_manager = DataManager(config)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一位经验丰富的肺部肿瘤科医生，专门从事肺癌三期患者的诊疗工作。

你的任务是基于患者的初始症状描述，通过调用相关医疗工具获取详细检查信息，最终给出准确的诊断和治疗建议。

可用的医疗工具包括：
- 胸部CT检查指标
- 肿瘤标志物检测
- 病理活检报告
- 基因检测结果
- 肺功能评估
- 影像学评价
- 临床分期评估
等15个专业工具

请按照以下步骤进行：
1. 仔细分析患者的初始症状和基本信息
2. 根据需要主动调用相关医疗工具获取详细检查结果
3. 综合所有信息，给出完整的诊断和治疗方案
4. 解释你的诊疗思路和决策依据

注意：初始描述只提供基本信息，具体的检查结果需要通过工具调用获取。"""
    
    def generate_diagnosis_report(self, patient_case: Dict[str, Any]) -> Dict[str, Any]:
        """生成单个患者的诊断报告"""
        patient_id = patient_case['patient_id']
        
        try:
            # 初始化对话
            conversation = self._init_conversation(patient_case)
            
            # 执行多轮对话和工具调用
            tool_calls = self._run_tool_calling_loop(conversation, patient_case)
            
            # 提取最终诊断
            final_response = self._extract_final_response(conversation)
            
            return {
                "patient_id": patient_id,
                "conversation": conversation,
                "tool_calls": tool_calls,
                "final_response": final_response,
                "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            raise MedicalBenchError(
                ErrorType.TOOL_ERROR,
                f"患者{patient_id}诊断生成失败",
                {"error": str(e)}
            )
    
    def _init_conversation(self, patient_case: Dict[str, Any]) -> List[Dict[str, str]]:
        """初始化对话"""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": patient_case['initial_query']}
        ]
    
    def _run_tool_calling_loop(self, conversation: List[Dict], patient_case: Dict[str, Any]) -> List[Dict]:
        """执行工具调用循环"""
        tool_calls = []
        
        for turn in range(self.config.max_turns):
            # 获取AI响应
            response = self.api_client.call_api(conversation)
            conversation.append({"role": "assistant", "content": response})
            
            # 检测是否需要工具调用
            tool_request = self._detect_tool_request(response)
            if not tool_request:
                break
            
            # 执行工具调用
            tool_result = self._execute_tool_call(tool_request, patient_case)
            tool_calls.append({
                "turn": turn + 1,
                "tool_request": tool_request,
                "tool_result": tool_result
            })
            
            # 将工具结果添加到对话
            conversation.append({
                "role": "user", 
                "content": f"工具调用结果：{json.dumps(tool_result, ensure_ascii=False)}"
            })
        
        return tool_calls
    
    def _detect_tool_request(self, response: str) -> Optional[Dict[str, Any]]:
        """检测工具调用请求"""
        # 简化的工具检测逻辑
        tool_keywords = {
            "胸部CT": "get_chest_ct_metrics",
            "肿瘤标志物": "get_tumor_markers", 
            "病理": "get_pathology_report",
            "基因检测": "get_genetic_testing",
            "肺功能": "get_pulmonary_function"
        }
        
        for keyword, tool_id in tool_keywords.items():
            if keyword in response:
                return {
                    "tool_id": tool_id,
                    "tool_name": keyword,
                    "detected_from": response[:100]
                }
        
        return None
    
    def _execute_tool_call(self, tool_request: Dict[str, Any], patient_case: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        tool_id = tool_request['tool_id']
        patient_id = patient_case['patient_id']
        
        # 从患者案例中获取工具结果
        tool_results_map = patient_case.get('tool_call_results_map', {})
        
        if tool_id in tool_results_map:
            return tool_results_map[tool_id]
        else:
            return {
                "status": "no_data_available",
                "message": f"患者{patient_id}的{tool_request['tool_name']}数据不可用"
            }
    
    def _extract_final_response(self, conversation: List[Dict]) -> str:
        """提取最终诊断响应"""
        # 获取最后一个assistant响应
        for message in reversed(conversation):
            if message['role'] == 'assistant':
                return message['content']
        return ""
    
    def evaluate_batch(self, patient_cases: List[Dict[str, Any]], max_workers: int = 4) -> List[Dict[str, Any]]:
        """批量评估患者案例"""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            with tqdm(total=len(patient_cases), desc="评估患者案例") as pbar:
                
                # 提交所有任务
                future_to_case = {
                    executor.submit(self.generate_diagnosis_report, case): case
                    for case in patient_cases
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_case):
                    case = future_to_case[future]
                    
                    try:
                        result = future.result()
                        results.append(result)
                        self.update_stats(processed=1)
                        
                    except Exception as e:
                        error_result = {
                            "patient_id": case['patient_id'],
                            "error": str(e),
                            "status": "failed"
                        }
                        results.append(error_result)
                        self.update_stats(failed=1)
                    
                    pbar.update(1)
        
        return results
    
    def generate(self) -> List[Dict[str, Any]]:
        """主生成方法"""
        # 加载患者案例数据
        patients_data, eval_data, initial_queries, tools_data = self.data_manager.load_all_data()
        
        # 构建患者案例
        patient_cases = []
        for patient in patients_data[:5]:  # 限制测试数量
            patient_id = str(patient['id'])
            
            case = {
                "patient_id": patient_id,
                "initial_query": initial_queries.get(patient_id, {}).get('initial_query', 
                    f"患者{patient['gender']}，{patient['age']}岁，请诊断和治疗建议"),
                "tool_call_results_map": {},  # 这里应该加载实际的工具结果
                "reference_conclusion": patient.get('result', ''),
                "metadata": {
                    "gender": patient['gender'],
                    "age": patient['age'],
                    "diagnosis": patient['diagnosis']
                }
            }
            patient_cases.append(case)
        
        # 执行批量评估
        results = self.evaluate_batch(patient_cases)
        
        # 保存结果
        output_file = self.config.results_dir / "evaluation_results.json"
        self.save_json(results, str(output_file))
        
        return results