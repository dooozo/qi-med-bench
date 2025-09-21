# QI-Med-Bench: 肺癌三期多轮工具调用评测系统

## 项目概述

QI-Med-Bench 是一个专门针对肺癌三期诊疗场景的AI模型评测系统，重点评测模型的**多轮工具调用**能力。系统基于86条真实肺癌患者数据，提供15个专业医疗工具，模拟真实的临床诊疗流程。

### 核心特色

1. **专业聚焦**：专门针对肺癌三期，而非泛化医疗场景
2. **多轮工具调用**：评测模型主动、按需调用工具的能力
3. **真实数据驱动**：基于86条真实患者病例
4. **纯数据返回**：工具返回客观指标，不提供医学建议
5. **精简初诊**：初始query只包含首诊信息，促使工具调用

## 系统架构

```
QI-Med-Bench/
├── 原始数据
│   ├── data.json              # 86条患者完整病例
│   └── eval_dataset.json      # 处理后的评测数据
├── 工具系统  
│   ├── qi_med_tools.json      # 15个医疗工具定义
│   └── medical_databases/     # 模拟数据库集合
├── 评测框架
│   ├── tau_bench/envs/medical/  # 医疗环境实现
│   ├── qi_med_evaluator.py      # 评测系统
│   └── patient_cases/           # 患者评测实例
└── 辅助脚本
    ├── generate_*.py            # 数据生成脚本
    └── test_qi_med_bench.py     # 系统测试
```

## 15个专业医疗工具

| 工具ID | 工具名称 | 功能描述 |
|--------|----------|----------|
| LC001 | get_chest_ct_metrics | 获取胸部CT客观指标 |
| LC002 | get_tumor_markers | 查询肿瘤标志物数值 |
| LC003 | get_pathology_data | 获取病理检查数据 |
| LC004 | get_genetic_mutations | 查询基因突变信息 |
| LC005 | get_pdl1_expression | 获取PD-L1表达水平 |
| LC006 | get_tnm_staging_details | 获取TNM分期详情 |
| LC007 | get_performance_status | 查询体能状态评分 |
| LC008 | get_pulmonary_function | 获取肺功能测量值 |
| LC009 | get_blood_routine | 查询血常规检验 |
| LC010 | get_liver_kidney_function | 获取肝肾功能数值 |
| LC011 | get_treatment_history | 查询既往治疗史 |
| LC012 | get_immune_adverse_events | 获取免疫不良反应 |
| LC013 | get_chemo_toxicity | 查询化疗毒副反应 |
| LC014 | get_radiation_parameters | 获取放疗物理参数 |
| LC015 | get_surgery_feasibility | 评估手术可行性 |

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install openai json time concurrent.futures

# 配置OpenRouter API密钥
export OPENROUTER_API_KEY="your_api_key_here"
```

### 2. 数据生成（如果需要）

```bash
# 生成医疗数据库（86个患者 × 15个工具）
python3 generate_medical_database.py

# 生成精简初始查询
python3 generate_initial_queries.py

# 生成完整患者评测实例
python3 generate_patient_cases.py
```

### 3. 运行评测

```bash
# 使用QI-Med评测器
python3 qi_med_evaluator.py --model "google/gemini-2.5-pro" --cases-file "all_patient_cases.json" --output-file "results.json"

# 或使用tau-bench框架
python3 run.py --env medical --model "gpt-4o" --model-provider openai --agent-strategy tool-calling
```

### 4. 系统测试

```bash
# 运行完整系统测试
python3 test_qi_med_bench.py
```

## 评测流程

### 1. 初始Query示例
```
患者女性，65岁，因咳嗽咳痰1月余就诊。
既往有10年吸烟史，已戒烟5年。
体检发现肺部阴影，无胸痛、咯血。
请问这位患者的诊疗方案应该是什么？
```

### 2. 模型工具调用流程
1. **分析初诊信息** → 识别需要获取的详细检查结果
2. **主动调用工具** → get_chest_ct_metrics, get_tumor_markers等
3. **获取客观数据** → 肿瘤大小35mm×23mm，CEA 8.5ng/ml等
4. **医学推理分析** → 基于工具返回的纯数据进行综合判断
5. **生成诊疗建议** → 提出具体的治疗方案

### 3. 评测标准
- **诊断准确性**：是否能基于工具数据得出正确诊断
- **工具调用完整性**：是否充分利用相关工具
- **治疗方案合理性**：建议的治疗是否符合临床指南
- **临床决策逻辑**：推理过程是否清晰合理

## 数据文件说明

### 核心数据文件

1. **data.json**：86条原始患者病例
   - 包含完整病史、诊断、治疗过程
   - 用于生成工具数据库和评测标准

2. **eval_dataset.json**：预处理的评测数据
   - 包含参考答案和评测标准
   - 按治疗类别分类（药物治疗、综合治疗、检查等）

3. **qi_med_tools.json**：15个工具的完整定义
   - 符合Function Calling的JSON Schema格式
   - 包含参数定义和输出格式

### 生成的数据文件

1. **medical_databases/**：每个工具的模拟数据库
   - 为每个患者预设了所有工具的返回结果
   - 确保评测的一致性和可重复性

2. **initial_queries.json**：86个精简的初始查询
   - 只包含首诊信息，促使工具调用
   - 去除了详细检查结果和治疗方案

3. **patient_cases/**：完整的患者评测实例
   - 包含初始query、工具结果映射、评测标准
   - 每个患者一个独立的JSON文件

## API使用示例

### 1. 直接使用QI-Med评测器

```python
from qi_med_evaluator import QIMedEvaluator

# 创建评测器
evaluator = QIMedEvaluator(model="google/gemini-2.5-pro")

# 加载患者案例
with open("all_patient_cases.json", 'r') as f:
    cases = json.load(f)

# 评测单个案例
result = evaluator.evaluate_single_case(cases[0])
print(f"Score: {result['evaluation']['total_score']}")
```

### 2. 集成到tau-bench框架

```python
from tau_bench.envs.medical import QIMedicalDomainEnv
from tau_bench.envs.user import UserStrategy

# 创建医疗环境
env = QIMedicalDomainEnv(
    user_strategy=UserStrategy.LLM,
    user_model="gpt-4o",
    task_split="test"
)

# 使用环境进行评测
print(f"Available tools: {len(env.tools_info)}")
print(f"Test cases: {len(env.tasks)}")
```

## 技术实现细节

### 1. 工具调用模拟
- 工具函数从预生成的数据库中查询结果
- 支持基于患者ID的精确匹配
- 返回结构化的医学指标数据

### 2. 多轮对话管理
- 检测模型的工具调用意图
- 自动返回对应的工具结果
- 支持最多10轮的对话交互

### 3. 评测指标计算
- 基于预设评测标准进行打分
- 支持加权总分计算
- 提供详细的评分说明

## 文件清单

### 核心系统文件
- `tau_bench/envs/medical/` - 医疗环境实现
- `qi_med_evaluator.py` - 独立评测系统
- `qi_med_tools.json` - 工具定义文件

### 数据生成脚本
- `generate_medical_database.py` - 数据库生成
- `generate_initial_queries.py` - 初始查询生成  
- `generate_patient_cases.py` - 患者案例生成

### 测试和演示
- `test_qi_med_bench.py` - 完整系统测试
- `demo_patient_cases.json` - 演示数据
- `demo_medical_databases/` - 演示数据库

### 配置文件
- `openrouter_minimal.py` - API配置示例
- `run.py` - tau-bench集成入口

## 使用建议

1. **首次使用**：运行 `test_qi_med_bench.py` 确保系统正常
2. **数据生成**：如果需要重新生成数据，按顺序运行生成脚本
3. **评测配置**：根据需要调整模型、并发数等参数
4. **结果分析**：关注工具调用模式和医学推理质量

## 注意事项

1. **API限制**：OpenRouter有速率限制，建议适当设置并发数
2. **数据隐私**：患者数据已脱敏处理
3. **医学免责**：本系统仅用于AI评测，不提供医疗建议
4. **版本兼容**：基于tau-bench框架，确保版本兼容性

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目地址：QI-Med-Bench
- 文档更新：2025年9月