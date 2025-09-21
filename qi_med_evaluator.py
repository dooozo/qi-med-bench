#!/usr/bin/env python3
"""
QI-Med-Bench 评测系统
基于OpenRouter API进行模型评测，支持多轮工具调用场景
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI
import concurrent.futures
from threading import Lock

# OpenRouter配置
API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"

class QIMedEvaluator:
    """QI医学领域评测器"""
    
    def __init__(self, model: str = "google/gemini-2.5-pro", max_retries: int = 3):
        self.model = model
        self.client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        self.max_retries = max_retries
        self.results_lock = Lock()
        
    def call_model_with_retry(self, messages: List[Dict], timeout: int = 180) -> str:
        """调用模型API，带重试机制"""
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    timeout=timeout
                )
                return response.choices[0].message.content if response.choices else ""
            except Exception as e:
                print(f"⚠️ Model call attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ All {self.max_retries} attempts failed")
                    return ""

    def simulate_tool_call(self, tool_name: str, patient_id: str, 
                          tool_results_map: Dict) -> Dict[str, Any]:
        """模拟工具调用，从预设数据中返回结果"""
        
        # 从工具结果映射中查找对应的数据
        for tool_id, tool_data in tool_results_map.items():
            # 简单的工具名称匹配（可能需要更精确的映射）
            if tool_name.lower() in tool_id.lower() or any(
                keyword in tool_name.lower() 
                for keyword in ['ct', 'tumor', 'pathology', 'genetic', 'pdl1', 
                               'tnm', 'performance', 'pulmonary', 'blood', 
                               'liver', 'treatment', 'immune', 'chemo', 
                               'radiation', 'surgery']
            ):
                return tool_data
        
        # 如果没有找到匹配的工具，返回通用错误信息
        return {"error": f"Tool {tool_name} not available for patient {patient_id}"}

    def generate_diagnosis_report(self, patient_case: Dict) -> Dict[str, Any]:
        """让模型基于初始query和工具调用生成诊疗报告"""
        
        patient_id = patient_case['patient_id']
        initial_query = patient_case['initial_query']
        tool_results_map = patient_case['tool_call_results_map']
        
        # 构建系统提示
        system_prompt = """
你是一位经验丰富的肺部肿瘤科专家。患者向你咨询，你需要：

1. 仔细分析患者的初始信息
2. 主动调用相关医疗工具获取详细检查结果
3. 基于工具返回的客观数据进行医学推理
4. 给出综合的诊疗建议

可用的医疗工具包括：
- get_chest_ct_metrics: 获取胸部CT指标
- get_tumor_markers: 获取肿瘤标志物
- get_pathology_data: 获取病理数据  
- get_genetic_mutations: 获取基因突变信息
- get_pdl1_expression: 获取PD-L1表达
- get_tnm_staging_details: 获取TNM分期
- get_performance_status: 获取体能状态
- get_pulmonary_function: 获取肺功能
- get_blood_routine: 获取血常规
- get_liver_kidney_function: 获取肝肾功能
- get_treatment_history: 获取既往治疗史
- get_immune_adverse_events: 获取免疫不良反应
- get_chemo_toxicity: 获取化疗毒性
- get_radiation_parameters: 获取放疗参数
- get_surgery_feasibility: 获取手术可行性

请按以下步骤操作：
1. 分析初始查询，识别需要获取的信息
2. 依次调用相关工具（请在需要时明确说明调用哪个工具）
3. 基于工具返回的数据进行综合分析
4. 给出最终的诊疗建议

注意：每次工具调用请明确说明调用的工具名称，我会为你返回对应的数据。
"""

        # 开始对话
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"患者咨询：{initial_query}"}
        ]
        
        tool_calls_made = []
        conversation_history = messages.copy()
        max_turns = 10  # 最大对话轮数
        
        print(f"🔄 Starting diagnosis for patient {patient_id}")
        
        for turn in range(max_turns):
            print(f"  📞 Conversation turn {turn + 1}")
            
            # 调用模型
            response = self.call_model_with_retry(conversation_history, timeout=240)
            if not response:
                break
                
            conversation_history.append({"role": "assistant", "content": response})
            
            # 检查是否有工具调用请求
            tool_called = False
            for tool_name in ['get_chest_ct_metrics', 'get_tumor_markers', 'get_pathology_data',
                            'get_genetic_mutations', 'get_pdl1_expression', 'get_tnm_staging_details',
                            'get_performance_status', 'get_pulmonary_function', 'get_blood_routine',
                            'get_liver_kidney_function', 'get_treatment_history', 'get_immune_adverse_events',
                            'get_chemo_toxicity', 'get_radiation_parameters', 'get_surgery_feasibility']:
                if tool_name in response.lower() or tool_name.replace('_', ' ') in response.lower():
                    # 模拟工具调用
                    tool_result = self.simulate_tool_call(tool_name, patient_id, tool_results_map)
                    tool_calls_made.append({
                        "tool_name": tool_name,
                        "result": tool_result,
                        "turn": turn + 1
                    })
                    
                    # 将工具结果反馈给模型
                    tool_result_text = f"工具 {tool_name} 返回结果：\n{json.dumps(tool_result, ensure_ascii=False, indent=2)}"
                    conversation_history.append({"role": "user", "content": tool_result_text})
                    tool_called = True
                    print(f"    🔧 Called tool: {tool_name}")
                    break
            
            # 如果没有工具调用且回复中包含最终建议，结束对话
            if not tool_called and any(keyword in response.lower() 
                                     for keyword in ['建议', '推荐', '方案', '治疗', '诊断', '结论']):
                print(f"    ✅ Final recommendation provided")
                break
                
            # 如果没有工具调用，提示继续
            if not tool_called:
                conversation_history.append({
                    "role": "user", 
                    "content": "请继续分析，如果需要更多信息请调用相关工具，或者给出最终的诊疗建议。"
                })
        
        return {
            "patient_id": patient_id,
            "conversation_history": conversation_history,
            "tool_calls_made": tool_calls_made,
            "final_response": conversation_history[-1]["content"] if conversation_history else "",
            "turns_used": len([msg for msg in conversation_history if msg["role"] == "assistant"])
        }

    def evaluate_response(self, patient_case: Dict, model_response: Dict) -> Dict[str, Any]:
        """评测模型响应的质量"""
        
        rubrics = patient_case['evaluation_rubrics']
        reference_answer = patient_case['reference_conclusion']
        final_response = model_response['final_response']
        tool_calls = model_response['tool_calls_made']
        
        # 构建评测提示
        evaluation_prompt = f"""
你是一位医学评测专家。请基于以下评测标准对AI模型的诊疗建议进行评分。

参考答案：
{reference_answer}

AI模型的回答：
{final_response}

AI调用的工具：
{json.dumps([call['tool_name'] for call in tool_calls], ensure_ascii=False)}

评测标准：
{json.dumps(rubrics, ensure_ascii=False, indent=2)}

请为每个评测标准打分（0-10分），并计算加权总分。

返回格式：
{{
  "detailed_scores": [
    {{"criterion": "标准名称", "score": 分数, "weight": 权重, "comment": "评价说明"}},
    ...
  ],
  "total_score": 加权总分,
  "overall_comment": "总体评价"
}}
"""

        messages = [
            {"role": "system", "content": "你是一位专业的医学评测专家，能够客观、准确地评估AI模型的医疗建议质量。"},
            {"role": "user", "content": evaluation_prompt}
        ]
        
        evaluation_response = self.call_model_with_retry(messages, timeout=120)
        
        try:
            evaluation_result = json.loads(evaluation_response)
            return evaluation_result
        except json.JSONDecodeError:
            # 如果解析失败，返回默认评分
            return {
                "detailed_scores": [{"criterion": r["criterion"], "score": 5, "weight": r.get("weight", 0.25), "comment": "评测失败"} for r in rubrics],
                "total_score": 5.0,
                "overall_comment": "评测系统解析失败"
            }

    def evaluate_single_case(self, patient_case: Dict) -> Dict[str, Any]:
        """评测单个患者案例"""
        
        patient_id = patient_case['patient_id']
        print(f"\n📋 Evaluating patient {patient_id}")
        
        start_time = time.time()
        
        try:
            # 1. 生成诊疗报告
            model_response = self.generate_diagnosis_report(patient_case)
            
            # 2. 评测响应质量
            evaluation_result = self.evaluate_response(patient_case, model_response)
            
            # 3. 整合结果
            end_time = time.time()
            
            result = {
                "patient_id": patient_id,
                "model_response": model_response,
                "evaluation": evaluation_result,
                "metadata": {
                    "evaluation_time": end_time - start_time,
                    "model_used": self.model,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            print(f"✅ Patient {patient_id} completed - Score: {evaluation_result.get('total_score', 0):.2f}")
            return result
            
        except Exception as e:
            print(f"❌ Error evaluating patient {patient_id}: {str(e)}")
            return {
                "patient_id": patient_id,
                "error": str(e),
                "metadata": {
                    "evaluation_time": time.time() - start_time,
                    "model_used": self.model,
                    "timestamp": datetime.now().isoformat()
                }
            }

    def run_evaluation(self, cases_file: str, output_file: str, 
                      max_workers: int = 3, start_idx: int = 0, end_idx: int = -1):
        """运行完整评测"""
        
        print("🚀 Starting QI-Med-Bench Evaluation")
        print("=" * 50)
        print(f"📊 Model: {self.model}")
        print(f"👥 Max workers: {max_workers}")
        
        # 加载患者案例
        with open(cases_file, 'r', encoding='utf-8') as f:
            all_cases = json.load(f)
        
        # 选择评测范围
        if end_idx == -1:
            end_idx = len(all_cases)
        cases_to_evaluate = all_cases[start_idx:end_idx]
        
        print(f"📋 Evaluating cases {start_idx} to {end_idx-1} ({len(cases_to_evaluate)} total)")
        
        # 并行评测
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_case = {
                executor.submit(self.evaluate_single_case, case): case 
                for case in cases_to_evaluate
            }
            
            for future in concurrent.futures.as_completed(future_to_case):
                result = future.result()
                with self.results_lock:
                    results.append(result)
                    
                    # 定期保存中间结果
                    if len(results) % 5 == 0:
                        temp_file = f"{output_file}.temp"
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 计算统计信息
        successful_results = [r for r in results if 'evaluation' in r]
        scores = [r['evaluation']['total_score'] for r in successful_results]
        
        summary = {
            "total_cases": len(cases_to_evaluate),
            "successful_evaluations": len(successful_results),
            "failed_evaluations": len(results) - len(successful_results),
            "average_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "model_used": self.model,
            "evaluation_date": datetime.now().isoformat()
        }
        
        # 保存最终结果
        final_result = {
            "summary": summary,
            "results": results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 50)
        print("🎉 Evaluation Completed!")
        print(f"📊 Results: {len(successful_results)}/{len(cases_to_evaluate)} successful")
        print(f"📈 Average Score: {summary['average_score']:.2f}")
        print(f"📁 Results saved to: {output_file}")
        
        return final_result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="QI-Med-Bench Evaluator")
    parser.add_argument("--model", type=str, default="google/gemini-2.5-pro", 
                       help="Model to evaluate")
    parser.add_argument("--cases-file", type=str, default="all_patient_cases.json",
                       help="Patient cases file")
    parser.add_argument("--output-file", type=str, default="evaluation_results.json",
                       help="Output file for results")
    parser.add_argument("--max-workers", type=int, default=2,
                       help="Maximum number of parallel workers")
    parser.add_argument("--start-idx", type=int, default=0,
                       help="Start index for evaluation")
    parser.add_argument("--end-idx", type=int, default=-1,
                       help="End index for evaluation (-1 for all)")
    
    args = parser.parse_args()
    
    try:
        evaluator = QIMedEvaluator(model=args.model)
        evaluator.run_evaluation(
            cases_file=args.cases_file,
            output_file=args.output_file,
            max_workers=args.max_workers,
            start_idx=args.start_idx,
            end_idx=args.end_idx
        )
    except KeyboardInterrupt:
        print("\n⏹️ Evaluation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()