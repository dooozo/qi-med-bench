#!/usr/bin/env python3
"""
QI-Med-Bench 主程序入口
重构后的统一入口点，支持数据生成、评估和监控
"""

import click
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from core import DataManager, QIMedEvaluator
from generators import (
    DatabaseGenerator, 
    QueryGenerator, 
    PatientCaseGenerator
)
from utils import setup_logging, ProgressMonitor

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@click.group()
@click.option('--debug', is_flag=True, help='启用调试模式')
@click.option('--config-file', type=click.Path(), help='配置文件路径')
def cli(debug: bool, config_file: str):
    """QI-Med-Bench - 医疗AI多轮工具调用评估系统"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        config.max_retries = 2
        config.timeout = 60
        logger.info("🐛 调试模式已启用")
    
    if config_file:
        logger.info(f"📄 加载配置文件: {config_file}")
        # TODO: 实现配置文件加载
    
    logger.info("🚀 QI-Med-Bench 系统启动")

@cli.command()
@click.option('--component', 
              type=click.Choice(['queries', 'databases', 'cases', 'all']),
              default='all',
              help='生成组件')
@click.option('--workers', default=8, help='并发线程数')
@click.option('--limit', type=int, help='限制处理数量（用于测试）')
def generate(component: str, workers: int, limit: int):
    """生成数据"""
    logger.info(f"📊 开始生成: {component}")
    
    # 更新配置
    config.max_workers = workers
    
    try:
        data_manager = DataManager(config)
        
        if component in ['queries', 'all']:
            logger.info("🔍 生成初始查询...")
            generator = QueryGenerator(config)
            patients_data = data_manager.load_patients_data()
            if limit:
                patients_data = patients_data[:limit]
            generator.generate_queries(patients_data)
        
        if component in ['databases', 'all']:
            logger.info("🏥 生成医疗数据库...")
            generator = DatabaseGenerator(config)
            generator.run()
        
        if component in ['cases', 'all']:
            logger.info("📋 生成患者案例...")
            generator = PatientCaseGenerator(config)
            generator.run()
        
        logger.info("✅ 数据生成完成")
        
    except Exception as e:
        logger.error(f"❌ 数据生成失败: {e}")
        sys.exit(1)

@cli.command()
@click.option('--patients', default=5, help='评估患者数量')
@click.option('--workers', default=4, help='并发线程数')
@click.option('--output', help='输出文件路径')
def evaluate(patients: int, workers: int, output: str):
    """运行评估"""
    logger.info(f"🩺 开始评估 {patients} 名患者")
    
    try:
        evaluator = QIMedEvaluator(config)
        
        # 加载患者案例数据并限制数量
        data_manager = DataManager(config)
        patients_data, _, initial_queries, _ = data_manager.load_all_data()
        
        # 构建评估案例
        cases = []
        for patient in patients_data[:patients]:
            patient_id = str(patient['id'])
            case = {
                "patient_id": patient_id,
                "initial_query": initial_queries.get(patient_id, {}).get('initial_query', 
                    f"患者{patient['gender']}，{patient['age']}岁，请给出诊疗方案"),
                "tool_call_results_map": {},
                "reference_conclusion": patient.get('result', ''),
                "metadata": {
                    "gender": patient['gender'],
                    "age": patient['age'],
                    "diagnosis": patient['diagnosis']
                }
            }
            cases.append(case)
        
        # 执行评估
        results = evaluator.evaluate_batch(cases, max_workers=workers)
        
        # 保存结果
        output_path = output or str(config.results_dir / "evaluation_results.json")
        evaluator.save_json(results, output_path)
        
        logger.info(f"✅ 评估完成，结果保存到: {output_path}")
        
        # 打印统计信息
        stats = evaluator.get_stats()
        logger.info(f"📊 评估统计: 成功 {stats['total_processed']}, 失败 {stats['total_failed']}")
        
    except Exception as e:
        logger.error(f"❌ 评估失败: {e}")
        sys.exit(1)

@cli.command()
@click.option('--interval', default=30, help='监控间隔（秒）')
def monitor(interval: int):
    """监控生成进度"""
    logger.info(f"📊 启动进度监控器 (间隔: {interval}s)")
    
    try:
        monitor = ProgressMonitor(config)
        monitor.run_monitoring_loop(interval)
    except KeyboardInterrupt:
        logger.info("👋 监控器已停止")
    except Exception as e:
        logger.error(f"❌ 监控失败: {e}")
        sys.exit(1)

@cli.command()
def status():
    """显示系统状态"""
    logger.info("📊 QI-Med-Bench 系统状态")
    
    try:
        data_manager = DataManager(config)
        
        # 检查数据文件
        files_status = {
            "患者数据": config.patients_file.exists(),
            "评测数据": config.eval_file.exists(), 
            "工具定义": config.tools_file.exists(),
            "初始查询": config.queries_file.exists()
        }
        
        print("\n📁 数据文件状态:")
        for name, exists in files_status.items():
            status_icon = "✅" if exists else "❌"
            print(f"  {status_icon} {name}")
        
        # 检查生成进度
        if config.db_dir.exists():
            db_files = list(config.db_dir.glob("*_database.json"))
            print(f"\n🏥 医疗数据库: {len(db_files)}/15 工具")
        
        if config.cases_dir.exists():
            case_files = list(config.cases_dir.glob("patient_*.json"))
            print(f"📋 患者案例: {len(case_files)}/86 案例")
        
        if config.results_dir.exists():
            result_files = list(config.results_dir.glob("*.json"))
            print(f"📊 评估结果: {len(result_files)} 文件")
        
    except Exception as e:
        logger.error(f"❌ 状态检查失败: {e}")
        sys.exit(1)

@cli.command()
@click.confirmation_option(prompt='确定要清理所有生成的文件吗？')
def clean():
    """清理生成的文件"""
    logger.info("🧹 清理生成文件...")
    
    import shutil
    
    dirs_to_clean = [
        config.db_dir,
        config.cases_dir, 
        config.results_dir
    ]
    
    files_to_clean = [
        config.queries_file,
        config.root_dir / "all_patient_cases.json",
        config.root_dir / "patient_cases_index.json"
    ]
    
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            logger.info(f"🗑️ 已删除目录: {dir_path}")
    
    for file_path in files_to_clean:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️ 已删除文件: {file_path}")
    
    logger.info("✅ 清理完成")

if __name__ == '__main__':
    cli()