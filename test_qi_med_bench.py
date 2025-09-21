#!/usr/bin/env python3
"""
QI-Med-Bench 完整系统测试脚本
测试整个工作流程：数据加载 -> 工具调用 -> 模型评测
"""

import json
import os
import sys
import time
from typing import Dict, List, Any

def test_data_loading():
    """测试数据加载"""
    print("🧪 Testing Data Loading...")
    
    required_files = [
        "data.json",
        "eval_dataset.json", 
        "qi_med_tools.json"
    ]
    
    for file_name in required_files:
        if os.path.exists(file_name):
            with open(file_name, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"  ✅ {file_name}: {len(data)} items")
        else:
            print(f"  ❌ {file_name}: Missing")
    
    # 检查生成的文件
    generated_files = {
        "initial_queries.json": "Initial queries",
        "all_patient_cases.json": "Patient cases",
        "medical_databases/database_index.json": "Database index"
    }
    
    for file_path, description in generated_files.items():
        if os.path.exists(file_path):
            print(f"  ✅ {description}: Generated")
        else:
            print(f"  ⏳ {description}: Not yet generated")

def test_medical_environment():
    """测试医疗环境"""
    print("\n🧪 Testing Medical Environment...")
    
    try:
        from tau_bench.envs.medical import QIMedicalDomainEnv
        from tau_bench.envs.user import UserStrategy
        
        # 创建环境实例
        env = QIMedicalDomainEnv(
            user_strategy=UserStrategy.LLM,
            user_model="gpt-4o",
            task_split="test"
        )
        
        print(f"  ✅ Environment created successfully")
        print(f"  📊 Tools available: {len(env.tools_info)}")
        print(f"  📋 Tasks loaded: {len(env.tasks)}")
        
        # 测试工具信息
        for i, tool in enumerate(env.tools_info[:3]):  # 显示前3个工具
            print(f"    🔧 Tool {i+1}: {tool['name']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Environment test failed: {e}")
        return False

def test_tool_functions():
    """测试工具函数"""
    print("\n🧪 Testing Tool Functions...")
    
    try:
        from tau_bench.envs.medical.tools.medical_tools import (
            get_chest_ct_metrics, get_tumor_markers, db_manager
        )
        
        # 测试数据库管理器
        print(f"  📊 Database manager loaded {len(db_manager.databases)} databases")
        
        # 测试工具调用（使用患者1作为示例）
        test_patient_id = "1"
        
        # 测试CT工具
        ct_result = get_chest_ct_metrics(test_patient_id)
        if ct_result:
            print(f"  ✅ CT metrics tool working")
        else:
            print(f"  ⚠️ CT metrics returned empty")
        
        # 测试肿瘤标志物工具
        marker_result = get_tumor_markers(test_patient_id)
        if marker_result:
            print(f"  ✅ Tumor markers tool working")
        else:
            print(f"  ⚠️ Tumor markers returned empty")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Tool functions test failed: {e}")
        return False

def test_tau_bench_integration():
    """测试与tau_bench框架的集成"""
    print("\n🧪 Testing Tau-Bench Integration...")
    
    try:
        from tau_bench.types import RunConfig
        from tau_bench.envs import get_env
        
        # 创建配置
        config = RunConfig(
            model_provider="openai",
            user_model_provider="openai", 
            model="gpt-4o",
            env="medical",
            agent_strategy="tool-calling",
            start_index=0,
            end_index=2  # 只测试前2个任务
        )
        
        print(f"  ✅ Config created: {config.env} environment")
        
        # 测试环境获取
        env = get_env(
            env_name="medical",
            user_strategy="llm",
            user_model="gpt-4o",
            task_split="test"
        )
        
        print(f"  ✅ Environment retrieved successfully")
        print(f"  📊 Available tools: {len(env.tools_info)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        return False

def test_evaluation_system():
    """测试评测系统"""
    print("\n🧪 Testing Evaluation System...")
    
    try:
        from qi_med_evaluator import QIMedEvaluator
        
        # 创建评测器
        evaluator = QIMedEvaluator(model="google/gemini-2.5-pro")
        print(f"  ✅ Evaluator created with model: {evaluator.model}")
        
        # 测试工具调用模拟
        test_tool_map = {
            "LC001": {"tumor_size": {"max_diameter_mm": 35}},
            "LC002": {"CEA_ng_ml": 5.2}
        }
        
        result = evaluator.simulate_tool_call("get_chest_ct_metrics", "1", test_tool_map)
        if result:
            print(f"  ✅ Tool call simulation working")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Evaluation system test failed: {e}")
        return False

def create_demo_data():
    """创建演示数据（如果生成的数据还未完成）"""
    print("\n🔧 Creating Demo Data...")
    
    # 创建最小化的演示数据库
    demo_db_dir = "demo_medical_databases"
    if not os.path.exists(demo_db_dir):
        os.makedirs(demo_db_dir)
    
    # 示例工具数据
    demo_tools = ["LC001", "LC002", "LC003"]
    demo_patients = ["1", "2", "3"]
    
    for tool_id in demo_tools:
        tool_db = {}
        for patient_id in demo_patients:
            if tool_id == "LC001":  # CT指标
                tool_db[patient_id] = {
                    "tumor_size": {"max_diameter_mm": 30 + int(patient_id) * 5, "volume_cm3": 15.5},
                    "pleural_invasion": True,
                    "lymph_nodes": [{"station": "4R", "size_mm": 12, "suv_value": 3.2}]
                }
            elif tool_id == "LC002":  # 肿瘤标志物
                tool_db[patient_id] = {
                    "CEA_ng_ml": 4.5 + int(patient_id) * 0.8,
                    "NSE_ng_ml": 15.2,
                    "CYFRA21_1_ng_ml": 3.1
                }
            elif tool_id == "LC003":  # 病理数据
                tool_db[patient_id] = {
                    "histology_type": "腺癌",
                    "differentiation_grade": "中分化",
                    "ki67_percentage": 60 + int(patient_id) * 5
                }
        
        # 保存工具数据库
        db_file = os.path.join(demo_db_dir, f"{tool_id}_demo_database.json")
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(tool_db, f, ensure_ascii=False, indent=2)
    
    # 创建索引文件
    index_data = {
        "tools": [{"tool_id": tid, "tool_name": f"demo_tool_{tid}"} for tid in demo_tools],
        "patients": demo_patients,
        "database_files": [f"{tid}_demo_database.json" for tid in demo_tools]
    }
    
    with open(os.path.join(demo_db_dir, "database_index.json"), 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ Demo database created in {demo_db_dir}")
    
    # 创建演示患者案例（如果不存在）
    if not os.path.exists("all_patient_cases.json"):
        demo_cases = []
        for i in range(3):
            case = {
                "patient_id": str(i + 1),
                "initial_query": f"患者{i+1}，65岁女性，因咳嗽咳痰1月余就诊，请问诊疗方案？",
                "tool_call_results_map": {
                    "LC001": {"tumor_size": {"max_diameter_mm": 30 + i * 5}},
                    "LC002": {"CEA_ng_ml": 4.5 + i * 0.8},
                    "LC003": {"histology_type": "腺癌"}
                },
                "reference_conclusion": "建议完善检查后制定综合治疗方案",
                "evaluation_rubrics": [
                    {"criterion": "诊断准确性", "description": "诊断是否准确", "weight": 0.4},
                    {"criterion": "治疗合理性", "description": "治疗方案是否合理", "weight": 0.6}
                ],
                "metadata": {"age": 65, "gender": "女", "diagnosis": "肺癌"}
            }
            demo_cases.append(case)
        
        with open("demo_patient_cases.json", 'w', encoding='utf-8') as f:
            json.dump(demo_cases, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ Demo patient cases created")

def run_mini_evaluation():
    """运行小规模评测演示"""
    print("\n🚀 Running Mini Evaluation Demo...")
    
    # 确保有演示数据
    if not os.path.exists("demo_patient_cases.json"):
        create_demo_data()
    
    try:
        # 修改数据库路径为演示数据库
        import tau_bench.envs.medical.tools.medical_tools as mt
        original_db_dir = mt.MedicalDatabaseManager.__init__
        
        def demo_init(self):
            self.databases = {}
            self.database_dir = "demo_medical_databases"
            self._load_databases()
        
        mt.MedicalDatabaseManager.__init__ = demo_init
        
        # 重新加载数据库管理器
        mt.db_manager = mt.MedicalDatabaseManager()
        
        from qi_med_evaluator import QIMedEvaluator
        
        evaluator = QIMedEvaluator(model="google/gemini-2.5-pro")
        
        # 加载演示案例
        with open("demo_patient_cases.json", 'r', encoding='utf-8') as f:
            demo_cases = json.load(f)
        
        print(f"  📋 Loaded {len(demo_cases)} demo cases")
        
        # 评测第一个案例
        print(f"\n  🧪 Testing case 1...")
        result = evaluator.evaluate_single_case(demo_cases[0])
        
        if 'evaluation' in result:
            score = result['evaluation'].get('total_score', 0)
            print(f"  ✅ Demo evaluation completed - Score: {score:.2f}")
            
            # 保存结果
            with open("demo_evaluation_result.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            return True
        else:
            print(f"  ❌ Demo evaluation failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Mini evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🎯 QI-Med-Bench System Test")
    print("=" * 50)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("Data Loading", test_data_loading),
        ("Medical Environment", test_medical_environment), 
        ("Tool Functions", test_tool_functions),
        ("Tau-Bench Integration", test_tau_bench_integration),
        ("Evaluation System", test_evaluation_system)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} crashed: {e}")
            test_results.append((test_name, False))
    
    # 创建演示数据
    create_demo_data()
    
    # 运行演示评测
    demo_result = run_mini_evaluation()
    test_results.append(("Demo Evaluation", demo_result))
    
    # 显示结果总结
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! QI-Med-Bench is ready!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()