"""
医疗数据库生成器 - 重构版本
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple
from tqdm import tqdm

from core.base import BaseGenerator
from core.data_manager import DataManager
from config import Config

class DatabaseGenerator(BaseGenerator):
    """医疗数据库生成器"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.data_manager = DataManager(config)
    
    def generate_tool_data(self, patient: Dict[str, Any], tool: Dict[str, Any]) -> Dict[str, Any]:
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
        return self.parse_json_response(response, f"Patient {patient['id']}, Tool {tool['tool_id']}")
    
    def process_patient_tool_pair(self, args: Tuple[Dict, Dict]) -> Tuple[str, str, Dict, bool]:
        """处理单个患者-工具对"""
        patient, tool = args
        
        try:
            result = self.generate_tool_data(patient, tool)
            self.update_stats(processed=1)
            return (patient['id'], tool['tool_id'], result, True)
            
        except Exception as e:
            self.logger.error(f"处理失败 - Patient {patient['id']}, Tool {tool['tool_id']}: {e}")
            self.update_stats(failed=1)
            return (patient['id'], tool['tool_id'], {}, False)
    
    def generate_databases_parallel(self, patients_data: List[Dict], tools: List[Dict]) -> Dict[str, Dict]:
        """并行生成所有数据库"""
        self.logger.info(f"🚀 启动多线程生成 - {self.config.max_workers} 线程")
        
        # 准备任务列表
        tasks = [(patient, tool) for patient in patients_data for tool in tools]
        total_tasks = len(tasks)
        
        self.logger.info(f"📊 总任务数: {total_tasks} ({len(patients_data)} 患者 × {len(tools)} 工具)")
        
        # 初始化数据库结构
        databases = {tool['tool_id']: {} for tool in tools}
        
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
                    stats = self.get_stats()
                    pbar.set_postfix({
                        '成功': stats['total_processed'],
                        '失败': stats['total_failed'], 
                        '速率': f"{stats['requests_per_second']:.1f}/s"
                    })
        
        return databases
    
    def save_databases(self, databases: Dict, tools: List[Dict], patients: List[Dict]) -> None:
        """保存数据库文件"""
        self.logger.info("💾 保存数据库文件...")
        
        # 保存各工具数据库
        for tool in tools:
            tool_id = tool['tool_id']
            tool_name = tool['tool_name']
            
            db_file = self.config.get_db_file(tool_id, tool_name)
            self.save_json(databases[tool_id], str(db_file))
            
            self.logger.info(f"✅ 保存 {tool_id} 数据库: {len(databases[tool_id])} 条记录")
        
        # 保存索引文件
        stats = self.get_stats()
        self.data_manager.save_database_index(tools, patients, stats)
    
    def generate(self) -> Dict[str, Dict]:
        """主生成方法"""
        # 加载数据
        patients_data, _, _, tools_data = self.data_manager.load_all_data()
        
        # 并行生成数据库
        databases = self.generate_databases_parallel(patients_data, tools_data)
        
        # 保存数据库
        self.save_databases(databases, tools_data, patients_data)
        
        return databases