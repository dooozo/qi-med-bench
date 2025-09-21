#!/usr/bin/env python3
"""
多线程医疗数据生成器 - 大幅提升生成速度
使用线程池并行处理患者数据，配置动态调整和进度监控
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from openai import OpenAI
from tqdm import tqdm
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """统一配置管理"""
    api_key: str = "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"
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemini-2.5-pro"
    
    # 多线程配置
    max_workers: int = 8          # 并发线程数
    max_retries: int = 5          # 增加重试次数
    timeout: int = 300            # 超长超时时间
    base_delay: float = 0.2       # 基础延迟
    
    # 速率限制
    requests_per_minute: int = 200
    batch_size: int = 10          # 批处理大小

class ThreadSafeAPIClient:
    """线程安全的API客户端"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        self.lock = Lock()
        self.request_times = []
        
    def call_api(self, messages: List[Dict], **kwargs) -> str:
        """线程安全的API调用"""
        self._rate_limit()
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=0.3,
                    timeout=self.config.timeout,
                    **kwargs
                )
                return response.choices[0].message.content if response.choices else ""
                
            except Exception as e:
                wait_time = self.config.base_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)[:100]}...")
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.config.max_retries} attempts failed")
                    return ""
    
    def _rate_limit(self):
        """速率限制"""
        with self.lock:
            now = time.time()
            # 清理60秒前的请求记录
            self.request_times = [t for t in self.request_times if now - t < 60]
            
            # 如果请求过于频繁，等待
            if len(self.request_times) >= self.config.requests_per_minute:
                sleep_time = 60 - (now - self.request_times[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            self.request_times.append(now)

class ThreadedDatabaseGenerator:
    """多线程数据库生成器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_client = ThreadSafeAPIClient(config)
        self.stats = {
            'total_processed': 0,
            'total_failed': 0,
            'start_time': None
        }
        self.stats_lock = Lock()
        
    def generate_tool_data(self, patient: Dict, tool: Dict) -> Dict[str, Any]:
        """为单个患者和工具生成数据"""
        patient_info = f"患者{patient['id']}：{patient['gender']}, {patient['age']}岁, 诊断：{patient['diagnosis']}"
        
        prompt = f"""
你是一位经验丰富的医学数据工程师。请基于以下患者信息，为工具"{tool['tool_name']}"生成符合其output_schema的真实、合理的医疗数据。

患者信息：
{patient_info}

病例摘要：
{patient['summary']}

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
        
        response = self.api_client.call_api(messages)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"JSON解析失败 - Patient {patient['id']}, Tool {tool['tool_id']}")
            return {"status": "generation_failed", "raw_response": response[:200]}
    
    def process_patient_tool_pair(self, args: tuple) -> tuple:
        """处理单个患者-工具对"""
        patient, tool = args
        
        try:
            result = self.generate_tool_data(patient, tool)
            
            with self.stats_lock:
                self.stats['total_processed'] += 1
                
            return (patient['id'], tool['tool_id'], result, True)
            
        except Exception as e:
            logger.error(f"处理失败 - Patient {patient['id']}, Tool {tool['tool_id']}: {e}")
            
            with self.stats_lock:
                self.stats['total_failed'] += 1
                
            return (patient['id'], tool['tool_id'], {}, False)
    
    def generate_databases_parallel(self, patients_data: List[Dict], tools: List[Dict]):
        """并行生成所有数据库"""
        logger.info(f"🚀 启动多线程生成 - {self.config.max_workers} 线程")
        
        # 创建输出目录
        db_dir = "medical_databases"
        os.makedirs(db_dir, exist_ok=True)
        
        # 准备任务列表
        tasks = [(patient, tool) for patient in patients_data for tool in tools]
        total_tasks = len(tasks)
        
        logger.info(f"📊 总任务数: {total_tasks} ({len(patients_data)} 患者 × {len(tools)} 工具)")
        
        # 初始化数据库结构
        databases = {tool['tool_id']: {} for tool in tools}
        self.stats['start_time'] = time.time()
        
        # 执行并行任务
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            with tqdm(total=total_tasks, desc="生成医疗数据") as pbar:
                
                # 提交所有任务
                future_to_task = {
                    executor.submit(self.process_patient_tool_pair, task): task 
                    for task in tasks
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_task):
                    patient_id, tool_id, result, success = future.result()
                    
                    if success:
                        databases[tool_id][str(patient_id)] = result
                    
                    # 更新进度条
                    pbar.update(1)
                    elapsed = time.time() - self.stats['start_time']
                    rate = self.stats['total_processed'] / elapsed if elapsed > 0 else 0
                    pbar.set_postfix({
                        '成功': self.stats['total_processed'],
                        '失败': self.stats['total_failed'], 
                        '速率': f"{rate:.1f}/s"
                    })
        
        # 保存数据库文件
        self._save_databases(databases, tools, db_dir)
        
        return databases
    
    def _save_databases(self, databases: Dict, tools: List[Dict], db_dir: str):
        """保存数据库文件"""
        logger.info("💾 保存数据库文件...")
        
        # 保存各工具数据库
        db_files = []
        for tool in tools:
            tool_id = tool['tool_id']
            tool_name = tool['tool_name']
            
            db_file = f"{tool_id}_{tool_name}_database.json"
            db_path = os.path.join(db_dir, db_file)
            
            with open(db_path, 'w', encoding='utf-8') as f:
                json.dump(databases[tool_id], f, ensure_ascii=False, indent=2)
            
            db_files.append(db_file)
            logger.info(f"✅ 保存 {tool_id} 数据库: {len(databases[tool_id])} 条记录")
        
        # 保存索引文件
        index_data = {
            "tools": [{"tool_id": tool['tool_id'], "tool_name": tool['tool_name']} for tool in tools],
            "patients": list(databases[tools[0]['tool_id']].keys()),
            "database_files": db_files,
            "generation_stats": {
                "total_processed": self.stats['total_processed'],
                "total_failed": self.stats['total_failed'],
                "duration_seconds": time.time() - self.stats['start_time'],
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        with open(os.path.join(db_dir, "database_index.json"), 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

class ThreadedPatientCaseGenerator:
    """多线程患者案例生成器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_client = ThreadSafeAPIClient(config)
    
    def generate_evaluation_rubrics(self, patient_data: Dict, eval_item: Dict) -> List[Dict]:
        """生成评测标准"""
        prompt = f"""
你是一位医学评测专家。请基于以下信息生成详细的评测标准（rubrics）。

患者信息：
- ID: {patient_data['id']}
- 诊断: {patient_data['diagnosis']}
- 治疗标签: {patient_data['label']}

参考答案：
{eval_item.get('reference_answer', patient_data['result'])}

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
        
        response = self.api_client.call_api(messages)
        
        try:
            rubrics = json.loads(response)
            # 验证权重总和
            total_weight = sum(r.get('weight', 0) for r in rubrics)
            if abs(total_weight - 1.0) > 0.1:
                for r in rubrics:
                    r['weight'] = r.get('weight', 0) / total_weight if total_weight > 0 else 1.0/len(rubrics)
            return rubrics
        except json.JSONDecodeError:
            return [
                {"criterion": "诊断准确性", "description": "诊断是否准确", "weight": 0.3},
                {"criterion": "治疗方案合理性", "description": "治疗方案是否合理", "weight": 0.3},
                {"criterion": "工具调用完整性", "description": "是否充分利用工具获取信息", "weight": 0.2},
                {"criterion": "临床决策逻辑", "description": "决策过程是否逻辑清晰", "weight": 0.2}
            ]

def load_all_data():
    """加载所有需要的数据文件"""
    logger.info("📂 加载数据文件...")
    
    with open('data.json', 'r', encoding='utf-8') as f:
        patients_data = json.load(f)
    
    with open('eval_dataset.json', 'r', encoding='utf-8') as f:
        eval_data = json.load(f)
    
    with open('qi_med_tools.json', 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    
    initial_queries = {}
    if os.path.exists('initial_queries.json'):
        with open('initial_queries.json', 'r', encoding='utf-8') as f:
            queries_list = json.load(f)
            for query in queries_list:
                initial_queries[query['patient_id']] = query
    
    logger.info(f"✅ 加载完成: {len(patients_data)} 患者, {len(eval_data)} 评测, {len(tools_data['tools'])} 工具")
    
    return patients_data, eval_data, initial_queries, tools_data['tools']

def main():
    """主函数"""
    print("🚀 多线程医疗数据生成器启动")
    print("=" * 60)
    
    config = Config()
    
    try:
        # 加载数据
        patients_data, eval_data, initial_queries, tools = load_all_data()
        
        # 生成医疗数据库
        logger.info("🏗️ 开始生成医疗数据库...")
        db_generator = ThreadedDatabaseGenerator(config)
        databases = db_generator.generate_databases_parallel(patients_data, tools)
        
        elapsed = time.time() - db_generator.stats['start_time']
        logger.info(f"🎉 数据库生成完成! 用时 {elapsed:.1f}s")
        logger.info(f"📊 成功: {db_generator.stats['total_processed']}, 失败: {db_generator.stats['total_failed']}")
        
        print("\n" + "=" * 60)
        print("✅ 多线程数据生成完成!")
        print(f"⚡ 速度提升约 {config.max_workers}x")
        print("📁 数据已保存到 medical_databases/ 目录")
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        logger.error(f"生成失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()