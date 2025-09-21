#!/usr/bin/env python3
"""
使用OpenRouter API从完整病例摘要生成精简的初始query
只包含首诊时医生能获得的基本信息，促使模型主动调用工具获取详细检查结果
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

def generate_initial_query(patient: Dict) -> str:
    """为单个患者生成精简的初始query"""
    
    prompt = f"""
你是一位经验丰富的肺部肿瘤科医生。请基于以下完整病例信息，生成一个精简的"首诊问诊"场景描述。

完整病例：
- 患者ID: {patient['id']}
- 性别: {patient['gender']}
- 年龄: {patient['age']}岁
- 诊断: {patient['diagnosis']}
- 完整病史: {patient['summary']}

要求：
1. **只包含首诊时通过问诊和简单查体能获得的信息**：
   - 患者基本信息（年龄、性别）
   - 主诉症状（咳嗽、胸痛、呼吸困难等）
   - 简单既往史（吸烟史、家族史等）
   - 就诊原因（体检发现、症状就诊等）

2. **不能包含的信息**（这些需要通过工具调用获取）：
   - 具体的CT、病理、基因检测结果
   - 详细的实验室指标数值
   - 具体的治疗方案和疗效评价
   - TNM分期的具体数据
   - 肿瘤标志物数值

3. **输出格式**：
   - 以"患者XXX，XX岁XX性，因XX就诊"开头
   - 简洁描述主诉和简单病史
   - 以"请问这位患者的诊疗方案应该是什么？"结尾
   - 总长度控制在200字以内

4. **目的**：生成的query应该迫使AI模型主动调用工具来获取CT、病理、基因检测等详细信息，才能给出准确的诊疗建议。

请生成精简的初始query：
"""

    messages = [
        {"role": "system", "content": "你是一位专业的肺部肿瘤科医生，擅长从完整病例中提取首诊时的关键信息。"},
        {"role": "user", "content": prompt}
    ]
    
    print(f"🔄 Generating initial query for patient {patient['id']}...")
    response = call_openrouter_with_retry(messages, timeout=60)
    return response.strip()

def generate_all_queries():
    """生成所有患者的初始query"""
    print("🚀 Starting Initial Query Generation")
    print("=" * 50)
    
    # 加载原始数据
    print("📂 Loading patient data...")
    with open('data.json', 'r', encoding='utf-8') as f:
        patients_data = json.load(f)
    print(f"✅ Loaded {len(patients_data)} patients")
    
    # 生成初始queries
    initial_queries = []
    
    for i, patient in enumerate(patients_data):
        print(f"\n📋 Processing patient {patient['id']} ({i+1}/{len(patients_data)})")
        
        # 生成精简query
        initial_query = generate_initial_query(patient)
        
        if initial_query:
            query_data = {
                "patient_id": str(patient['id']),
                "original_diagnosis": patient['diagnosis'],
                "original_label": patient['label'],
                "initial_query": initial_query,
                "metadata": {
                    "gender": patient['gender'],
                    "age": patient['age'],
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            initial_queries.append(query_data)
            print(f"✅ Generated query for patient {patient['id']}")
        else:
            print(f"❌ Failed to generate query for patient {patient['id']}")
        
        # 避免API限速
        time.sleep(1)
    
    # 保存结果
    output_file = "initial_queries.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(initial_queries, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print("🎉 Initial Query Generation Completed!")
    print(f"📊 Generated {len(initial_queries)} initial queries")
    print(f"📁 Saved to: {output_file}")
    
    # 显示几个示例
    print("\n📝 Sample Generated Queries:")
    for i, query in enumerate(initial_queries[:3]):
        print(f"\nSample {i+1}:")
        print(f"Patient ID: {query['patient_id']}")
        print(f"Query: {query['initial_query']}")

def main():
    """主函数"""
    try:
        generate_all_queries()
    except KeyboardInterrupt:
        print("\n⏹️ Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during generation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()