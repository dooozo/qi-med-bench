#!/usr/bin/env python3
"""
基于86条原始患者数据和15个医疗工具定义，使用OpenRouter API生成模拟数据库
"""

import json
import os
import sys
from openai import OpenAI
import time
import random
from typing import Dict, List, Any

# OpenRouter配置
API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "google/gemini-2.5-pro"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def load_data():
    """加载原始数据和工具定义"""
    print("📂 Loading data files...")
    
    with open('data.json', 'r', encoding='utf-8') as f:
        patients_data = json.load(f)
    
    with open('qi_med_tools.json', 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    
    print(f"✅ Loaded {len(patients_data)} patients and {len(tools_data['tools'])} tools")
    return patients_data, tools_data['tools']

def call_openrouter_with_retry(messages: List[Dict], max_retries: int = 3, timeout: int = 120) -> str:
    """调用OpenRouter API，带重试机制"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.3,
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

def generate_tool_data(patient: Dict, tool: Dict) -> Dict:
    """为单个患者和工具生成模拟数据"""
    patient_summary = patient['summary']
    patient_info = f"患者{patient['id']}：{patient['gender']}, {patient['age']}岁, 诊断：{patient['diagnosis']}"
    
    prompt = f"""
你是一位经验丰富的医学数据工程师。请基于以下患者信息，为工具"{tool['tool_name']}"生成符合其output_schema的真实、合理的医疗数据。

患者信息：
{patient_info}

病例摘要：
{patient_summary}

工具定义：
- 工具名称：{tool['tool_name']}
- 工具描述：{tool['tool_description']}
- 输出格式：{json.dumps(tool['output_schema'], ensure_ascii=False, indent=2)}

要求：
1. 生成的数据必须严格符合output_schema的格式
2. 数值应该在医学上合理（例如：肿瘤大小、实验室指标等）
3. 如果患者摘要中没有相关信息，请基于其诊断、年龄、性别等推测合理数值
4. 对于肺癌三期患者，数据应该体现典型的疾病特征
5. 直接返回JSON格式的数据，不要包含任何解释

请生成数据：
"""

    messages = [
        {"role": "system", "content": "你是一位专业的医学数据工程师，擅长基于患者信息生成符合医学标准的结构化数据。"},
        {"role": "user", "content": prompt}
    ]
    
    print(f"🔄 Generating data for patient {patient['id']}, tool {tool['tool_id']}...")
    response = call_openrouter_with_retry(messages, timeout=180)
    
    try:
        # 尝试解析JSON响应
        tool_data = json.loads(response)
        return tool_data
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parsing failed for patient {patient['id']}, tool {tool['tool_id']}: {e}")
        # 如果解析失败，返回一个基础的空结构
        return {}

def generate_database(patients_data: List[Dict], tools: List[Dict]):
    """生成完整的模拟数据库"""
    print("🏗️ Starting database generation...")
    
    # 创建数据库目录
    db_dir = "medical_databases"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # 为每个工具生成数据库文件
    databases = {}
    
    for tool in tools:
        tool_id = tool['tool_id']
        tool_name = tool['tool_name']
        print(f"\n🔧 Processing tool: {tool_id} - {tool_name}")
        
        tool_database = {}
        
        for i, patient in enumerate(patients_data):
            patient_id = str(patient['id'])
            print(f"  📋 Patient {patient_id} ({i+1}/{len(patients_data)})")
            
            # 生成该患者的工具数据
            tool_data = generate_tool_data(patient, tool)
            tool_database[patient_id] = tool_data
            
            # 避免API限速
            time.sleep(1)
        
        # 保存工具数据库
        db_file = f"{db_dir}/{tool_id}_{tool_name}_database.json"
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(tool_database, f, ensure_ascii=False, indent=2)
        
        databases[tool_id] = tool_database
        print(f"✅ Saved {tool_id} database to {db_file}")
    
    # 保存完整数据库索引
    index_file = f"{db_dir}/database_index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump({
            "tools": [{"tool_id": tool['tool_id'], "tool_name": tool['tool_name']} for tool in tools],
            "patients": [str(p['id']) for p in patients_data],
            "database_files": [f"{tool['tool_id']}_{tool['tool_name']}_database.json" for tool in tools]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved database index to {index_file}")
    return databases

def main():
    """主函数"""
    print("🚀 Starting Medical Database Generation")
    print("=" * 50)
    
    try:
        # 加载数据
        patients_data, tools = load_data()
        
        # 生成数据库
        databases = generate_database(patients_data, tools)
        
        print("\n" + "=" * 50)
        print("🎉 Database generation completed successfully!")
        print(f"📊 Generated databases for {len(tools)} tools and {len(patients_data)} patients")
        print("📁 Files saved in 'medical_databases/' directory")
        
    except KeyboardInterrupt:
        print("\n⏹️ Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during generation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()