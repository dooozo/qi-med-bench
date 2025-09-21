#!/usr/bin/env python3
"""
后台进程监控器 - 实时监控数据生成进度
"""

import json
import os
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class ProgressMonitor:
    """进度监控器"""
    
    def __init__(self):
        self.start_time = time.time()
        
    def check_file_progress(self, file_path: str, expected_count: int) -> Dict:
        """检查文件生成进度"""
        if not os.path.exists(file_path):
            return {"status": "not_found", "progress": 0, "count": 0}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict):
                count = len(data)
            else:
                count = 1
                
            progress = (count / expected_count * 100) if expected_count > 0 else 0
            
            return {
                "status": "exists",
                "progress": min(progress, 100),
                "count": count,
                "expected": expected_count
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "progress": 0}
    
    def check_database_progress(self) -> Dict:
        """检查医疗数据库生成进度"""
        db_dir = "medical_databases"
        index_path = os.path.join(db_dir, "database_index.json")
        
        if not os.path.exists(index_path):
            # 检查单个数据库文件
            completed_tools = 0
            if os.path.exists(db_dir):
                db_files = [f for f in os.listdir(db_dir) if f.endswith('_database.json')]
                completed_tools = len(db_files)
            
            return {
                "status": "in_progress",
                "completed_tools": completed_tools,
                "total_tools": 15,
                "progress": completed_tools / 15 * 100,
                "estimated_remaining": None
            }
        
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            total_tools = len(index_data.get('tools', []))
            completed_tools = len(index_data.get('database_files', []))
            
            return {
                "status": "completed",
                "completed_tools": completed_tools,
                "total_tools": total_tools,
                "progress": 100,
                "generation_stats": index_data.get('generation_stats', {})
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def check_patient_cases_progress(self) -> Dict:
        """检查患者案例生成进度"""
        cases_dir = "patient_cases"
        summary_file = "all_patient_cases.json"
        
        # 检查汇总文件
        summary_progress = self.check_file_progress(summary_file, 86)
        
        # 检查单个案例文件
        individual_count = 0
        if os.path.exists(cases_dir):
            case_files = [f for f in os.listdir(cases_dir) if f.startswith('patient_') and f.endswith('.json')]
            individual_count = len(case_files)
        
        return {
            "summary_file": summary_progress,
            "individual_files": {
                "count": individual_count,
                "expected": 86,
                "progress": individual_count / 86 * 100
            }
        }
    
    def estimate_completion_time(self, progress: float, elapsed_time: float) -> Optional[str]:
        """估算完成时间"""
        if progress <= 0:
            return None
        
        total_time = elapsed_time / (progress / 100)
        remaining_time = total_time - elapsed_time
        
        if remaining_time <= 0:
            return "即将完成"
        
        remaining_td = timedelta(seconds=int(remaining_time))
        
        # 格式化剩余时间
        hours = remaining_td.seconds // 3600
        minutes = (remaining_td.seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        elif minutes > 0:
            return f"{minutes}分钟"
        else:
            return "不到1分钟"
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available": f"{memory.available / (1024**3):.1f} GB",
                "disk_usage": disk.percent,
                "disk_free": f"{disk.free / (1024**3):.1f} GB"
            }
        except Exception:
            return {"status": "unavailable"}
    
    def print_status_report(self):
        """打印状态报告"""
        elapsed = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print(f"📊 QI-Med-Bench 数据生成进度报告")
        print(f"⏰ 运行时间: {timedelta(seconds=int(elapsed))}")
        print("=" * 60)
        
        # 1. 初始查询进度
        queries_progress = self.check_file_progress('initial_queries.json', 86)
        print(f"\n🔍 初始查询生成:")
        if queries_progress['status'] == 'exists':
            print(f"   ✅ 已完成 {queries_progress['count']}/86 ({queries_progress['progress']:.1f}%)")
        else:
            print(f"   ⏳ 状态: {queries_progress['status']}")
        
        # 2. 医疗数据库进度
        db_progress = self.check_database_progress()
        print(f"\n🏥 医疗数据库生成:")
        print(f"   📈 进度: {db_progress['completed_tools']}/{db_progress['total_tools']} 工具 ({db_progress['progress']:.1f}%)")
        
        if db_progress['progress'] < 100:
            remaining_tools = db_progress['total_tools'] - db_progress['completed_tools']
            print(f"   ⏳ 剩余: {remaining_tools} 工具")
            
            # 估算完成时间（假设每个工具86个患者，每个患者1秒）
            if db_progress['progress'] > 0:
                estimated = self.estimate_completion_time(db_progress['progress'], elapsed)
                if estimated:
                    print(f"   🕐 预计还需: {estimated}")
        else:
            stats = db_progress.get('generation_stats', {})
            if stats:
                print(f"   ✅ 生成完成! 用时: {stats.get('duration_seconds', 0):.1f}s")
                print(f"   📊 统计: 成功 {stats.get('total_processed', 0)}, 失败 {stats.get('total_failed', 0)}")
        
        # 3. 患者案例进度
        cases_progress = self.check_patient_cases_progress()
        print(f"\n📋 患者案例生成:")
        
        summary = cases_progress['summary_file']
        individual = cases_progress['individual_files']
        
        if summary['status'] == 'exists':
            print(f"   📄 汇总文件: {summary['count']}/86 案例 ({summary['progress']:.1f}%)")
        else:
            print(f"   📄 汇总文件: 未找到")
        
        print(f"   📁 单个文件: {individual['count']}/86 文件 ({individual['progress']:.1f}%)")
        
        if individual['progress'] < 100 and individual['progress'] > 0:
            estimated = self.estimate_completion_time(individual['progress'], elapsed)
            if estimated:
                print(f"   🕐 预计还需: {estimated}")
        
        # 4. 系统状态
        system = self.get_system_status()
        if system.get('cpu_usage') is not None:
            print(f"\n💻 系统状态:")
            print(f"   🔥 CPU: {system['cpu_usage']:.1f}%")
            print(f"   🧠 内存: {system['memory_usage']:.1f}% (可用: {system['memory_available']})")
            print(f"   💾 磁盘: {system['disk_usage']:.1f}% (可用: {system['disk_free']})")
        
        print("\n" + "=" * 60)

def main():
    """主监控循环"""
    monitor = ProgressMonitor()
    
    print("🚀 启动进度监控器...")
    print("📝 每30秒自动刷新状态")
    print("💡 按 Ctrl+C 退出监控")
    
    try:
        while True:
            monitor.print_status_report()
            
            # 检查是否全部完成
            db_progress = monitor.check_database_progress()
            cases_progress = monitor.check_patient_cases_progress()
            
            if (db_progress['progress'] >= 100 and 
                cases_progress['individual_files']['progress'] >= 100):
                print("\n🎉 所有数据生成任务已完成!")
                break
            
            print(f"\n⏳ 等待30秒后刷新...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n👋 监控器已退出")

if __name__ == "__main__":
    main()