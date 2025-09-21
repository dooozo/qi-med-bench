#!/usr/bin/env python3
"""
生成每个患者的完整评测实例文件
整合初始query、工具数据库、参考答案和评测标准
"""

import json
import os
import sys
from openai import OpenAI
import time
from typing import Dict, List, Any

# OpenRouter配置
API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "google/gemini-2.5-pro"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def call_openrouter_with_retry(messages: List[Dict], max_retries: int = 3, timeout: int = 120) -> str:
    """调用OpenRouter API，带重试机制"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.2,
                timeout=timeout
            )
            return response.choices[0].message.content if response.choices else ""
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"🔄 Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"❌ All {max_retries} attempts failed for API call")
                return ""

def load_all_data():
    """加载所有需要的数据文件"""
    print("📂 Loading all data files...")
    
    # 1. 加载原始患者数据
    with open('data.json', 'r', encoding='utf-8') as f:
        patients_data = json.load(f)
    
    # 2. 加载eval数据集（包含参考答案和评测标准）
    with open('eval_dataset.json', 'r', encoding='utf-8') as f:
        eval_data = json.load(f)
    
    # 3. 加载初始queries（如果存在）
    initial_queries = {}
    if os.path.exists('initial_queries.json'):
        with open('initial_queries.json', 'r', encoding='utf-8') as f:
            queries_list = json.load(f)
            for query in queries_list:
                initial_queries[query['patient_id']] = query
    
    # 4. 加载工具定义
    with open('qi_med_tools.json', 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    
    # 5. 加载医疗数据库
    databases = {}
    db_dir = "medical_databases"
    if os.path.exists(db_dir):
        index_file = os.path.join(db_dir, "database_index.json")
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            for db_file in index_data.get('database_files', []):
                db_path = os.path.join(db_dir, db_file)
                if os.path.exists(db_path):
                    tool_id = db_file.split('_')[0]
                    with open(db_path, 'r', encoding='utf-8') as f:
                        databases[tool_id] = json.load(f)
    
    print(f"✅ Loaded {len(patients_data)} patients, {len(eval_data)} eval entries")
    print(f"   {len(initial_queries)} initial queries, {len(databases)} tool databases")
    
    return patients_data, eval_data, initial_queries, tools_data, databases

def generate_evaluation_rubrics(patient_data: Dict, eval_item: Dict) -> List[Dict]:
    """基于患者数据和参考答案生成评测标准"""
    
    prompt = f"""
你是一位医学评测专家。请基于以下信息生成详细的评测标准（rubrics）。

患者信息：
- ID: {patient_data['id']}
- 诊断: {patient_data['diagnosis']}
- 治疗标签: {patient_data['label']}

参考答案：
{eval_item.get('reference_answer', patient_data['result'])}

现有评测标准：
{json.dumps(eval_item.get('rubrics', []), ensure_ascii=False, indent=2)}

要求生成3-5个具体的评测标准，每个标准包含：
1. criterion: 评测点名称
2. description: 详细描述
3. weight: 权重(0.1-0.4之间)

确保权重总和为1.0，标准应涵盖：
- 诊断准确性
- 治疗方案合理性  
- 工具调用完整性
- 临床决策逻辑

直接返回JSON格式的列表：
"""

    messages = [
        {"role": "system", "content": "你是一位专业的医学评测专家，擅长制定客观、全面的评测标准。"},
        {"role": "user", "content": prompt}
    ]
    
    response = call_openrouter_with_retry(messages, timeout=60)
    
    try:
        rubrics = json.loads(response)
        # 验证权重总和
        total_weight = sum(r.get('weight', 0) for r in rubrics)
        if abs(total_weight - 1.0) > 0.1:
            # 归一化权重
            for r in rubrics:
                r['weight'] = r.get('weight', 0) / total_weight if total_weight > 0 else 1.0/len(rubrics)
        return rubrics
    except json.JSONDecodeError:
        # 如果解析失败，使用默认标准
        return [
            {"criterion": "诊断准确性", "description": "诊断是否准确", "weight": 0.3},
            {"criterion": "治疗方案合理性", "description": "治疗方案是否合理", "weight": 0.3},
            {"criterion": "工具调用完整性", "description": "是否充分利用工具获取信息", "weight": 0.2},
            {"criterion": "临床决策逻辑", "description": "决策过程是否逻辑清晰", "weight": 0.2}
        ]

def create_patient_case(patient_data: Dict, eval_item: Dict, initial_query: Dict, 
                       tools_data: Dict, databases: Dict) -> Dict:
    """为单个患者创建完整的评测实例"""
    
    patient_id = str(patient_data['id'])
    print(f"📋 Creating case for patient {patient_id}")
    
    # 1. 获取初始query
    if initial_query:
        initial_query_text = initial_query['initial_query']
    else:
        # 如果没有生成的初始query，从eval数据集中提取或使用基本信息
        initial_query_text = f"患者{patient_data['gender']}，{patient_data['age']}岁，请问这位患者的诊疗方案应该是什么？"
    
    # 2. 构建工具调用结果映射
    tool_call_results_map = {}
    for tool in tools_data['tools']:
        tool_id = tool['tool_id']
        if tool_id in databases and patient_id in databases[tool_id]:
            tool_call_results_map[tool_id] = databases[tool_id][patient_id]
        else:
            # 如果没有数据，生成空结果
            tool_call_results_map[tool_id] = {"status": "no_data_available"}
    
    # 3. 生成评测标准
    evaluation_rubrics = generate_evaluation_rubrics(patient_data, eval_item)
    
    # 4. 构建完整的患者案例
    patient_case = {
        "patient_id": patient_id,
        "initial_query": initial_query_text,
        "tool_call_results_map": tool_call_results_map,
        "reference_conclusion": eval_item.get('reference_answer', patient_data['result']),
        "evaluation_rubrics": evaluation_rubrics,
        "metadata": {
            "gender": patient_data['gender'],
            "age": patient_data['age'],
            "diagnosis": patient_data['diagnosis'],
            "category": eval_item.get('category', patient_data['label']),
            "original_summary": patient_data['summary'],
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    return patient_case

def generate_all_patient_cases():
    """生成所有患者的评测实例"""
    print("🚀 Starting Patient Cases Generation")
    print("=" * 50)
    
    # 加载所有数据
    patients_data, eval_data, initial_queries, tools_data, databases = load_all_data()
    
    # 创建输出目录
    cases_dir = "patient_cases"
    if not os.path.exists(cases_dir):
        os.makedirs(cases_dir)
    
    # 创建eval数据的映射（按ID）
    eval_map = {}
    for item in eval_data:
        eval_map[str(item['id'])] = item
    
    # 生成每个患者的案例
    all_cases = []
    failed_cases = []
    
    for i, patient in enumerate(patients_data):
        patient_id = str(patient['id'])
        print(f"\n📋 Processing patient {patient_id} ({i+1}/{len(patients_data)})")
        
        try:
            # 获取对应的eval数据
            eval_item = eval_map.get(patient_id, {})
            
            # 获取初始query
            initial_query = initial_queries.get(patient_id, {})
            
            # 创建患者案例
            patient_case = create_patient_case(
                patient, eval_item, initial_query, tools_data, databases
            )
            
            # 保存单个案例文件
            case_file = os.path.join(cases_dir, f"patient_{patient_id}.json")
            with open(case_file, 'w', encoding='utf-8') as f:
                json.dump(patient_case, f, ensure_ascii=False, indent=2)
            
            all_cases.append(patient_case)
            print(f"✅ Generated case for patient {patient_id}")
            
            # 避免API限速
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Failed to generate case for patient {patient_id}: {e}")
            failed_cases.append(patient_id)
    
    # 保存所有案例的汇总文件
    summary_file = "all_patient_cases.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_cases, f, ensure_ascii=False, indent=2)
    
    # 保存案例索引
    index_data = {
        "total_cases": len(all_cases),
        "failed_cases": failed_cases,
        "cases_directory": cases_dir,
        "individual_files": [f"patient_{case['patient_id']}.json" for case in all_cases],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open("patient_cases_index.json", 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print("🎉 Patient Cases Generation Completed!")
    print(f"📊 Successfully generated {len(all_cases)} patient cases")
    print(f"❌ Failed cases: {len(failed_cases)}")
    print(f"📁 Individual cases saved in: {cases_dir}/")
    print(f"📁 Summary file: {summary_file}")
    print(f"📁 Index file: patient_cases_index.json")

def main():
    """主函数"""
    try:
        generate_all_patient_cases()
    except KeyboardInterrupt:
        print("\n⏹️ Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during generation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()