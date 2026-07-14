# EVOLUTION AI深度学习训练集文档

## 1. 概述

EVOLUTION AI深度学习模块用于支持AI辅助设计和智能优化功能，训练集是深度学习模型的核心基础。

## 2. 数据集架构

### 2.1 数据分类

| 数据类型 | 描述 | 用途 |
|----------|------|------|
| 设计参数数据 | 硬点参数、部件参数 | 参数预测、智能推荐 |
| 曲面质量数据 | 曲率、连续性指标 | 质量评估模型 |
| 设计风格数据 | 车型特征、风格标签 | 风格识别、生成式设计 |
| 用户行为数据 | 操作记录、偏好选择 | 用户画像、个性化推荐 |

### 2.2 数据存储

```
data/
├── training/                  # 训练数据
│   ├── parameters/            # 参数数据
│   ├── quality/               # 质量数据
│   ├── styles/                # 风格数据
│   └── behavior/              # 用户行为数据
├── validation/                # 验证数据
└── test/                      # 测试数据
```

## 3. 设计参数数据集

### 3.1 数据结构

```python
{
    "id": "param_001",
    "car_type": "sedan",
    "timestamp": "2026-07-14T10:00:00",
    "parameters": {
        "overall_length": 4800,
        "overall_width": 1900,
        "overall_height": 1450,
        "wheelbase": 2850,
        "track_width": 1650,
        "ground_clearance": 120,
        "overhang_front": 950,
        "overhang_rear": 1000,
        "front_axle": 950,
        "rear_axle": 3800,
        "waist_line": 650,
        "wheel_bulge": 80
    },
    "metadata": {
        "designer": "user_001",
        "project": "project_001",
        "quality_score": 92.5
    }
}
```

### 3.2 参数范围

| 参数 | 最小值 | 最大值 | 默认值 |
|------|--------|--------|--------|
| overall_length | 4000 | 5500 | 4800 |
| overall_width | 1700 | 2200 | 1900 |
| overall_height | 1300 | 1600 | 1450 |
| wheelbase | 2500 | 3200 | 2850 |
| track_width | 1400 | 1800 | 1650 |
| ground_clearance | 80 | 200 | 120 |
| overhang_front | 700 | 1200 | 950 |
| overhang_rear | 700 | 1300 | 1000 |

### 3.3 数据采集方法

1. **历史设计数据导入**：从现有设计项目中提取参数配置
2. **参数空间采样**：基于拉丁超立方采样生成参数组合
3. **用户交互记录**：记录用户在设计过程中的参数调整

## 4. 曲面质量数据集

### 4.1 数据结构

```python
{
    "id": "quality_001",
    "model_id": "model_001",
    "surface_type": "hood",
    "quality_metrics": {
        "continuity_g0": 1.0,
        "continuity_g1": 0.98,
        "continuity_g2": 0.95,
        "curvature_min": -0.001,
        "curvature_max": 0.002,
        "curvature_mean": 0.0005,
        "gaussian_curvature": 0.000001,
        "mean_curvature": 0.0002,
        "surface_smoothness": 0.92,
        "uv_alignment": 0.95
    },
    "mesh_data": {
        "num_faces": 1200,
        "num_vertices": 650,
        "aspect_ratio": 1.2
    }
}
```

### 4.2 质量指标计算方法

| 指标 | 计算方法 |
|------|----------|
| G0连续性 | 边界重合度检测 |
| G1连续性 | 法向量夹角计算 |
| G2连续性 | 曲率变化率分析 |
| 曲面平滑度 | 曲率方差评估 |
| UV对齐度 | 参数化质量评估 |

## 5. 设计风格数据集

### 5.1 数据结构

```python
{
    "id": "style_001",
    "car_type": "sedan",
    "style_tags": ["sporty", "elegant", "modern"],
    "feature_vector": [0.85, 0.23, 0.67, 0.45, 0.78, 0.12],
    "reference_images": ["img_001.jpg", "img_002.jpg"],
    "designer_notes": "运动型轿车设计，强调流线型车身"
}
```

### 5.2 风格标签体系

| 风格类别 | 标签 | 描述 |
|----------|------|------|
| 车型类型 | sedan, suv, coupe, hatchback | 车身类型 |
| 设计风格 | sporty, elegant, modern, classic | 设计语言 |
| 市场定位 | premium, economy, luxury, performance | 目标市场 |
| 能源类型 | ev, hybrid, gasoline | 动力系统 |

### 5.3 特征提取方法

1. **几何特征**：车身比例、线条特征
2. **美学特征**：曲面曲率分布、光影效果
3. **语义特征**：设计风格描述、标签分类

## 6. 用户行为数据集

### 6.1 数据结构

```python
{
    "id": "behavior_001",
    "user_id": "user_001",
    "session_id": "session_001",
    "timestamp": "2026-07-14T10:00:00",
    "action_type": "parameter_change",
    "action_details": {
        "parameter": "overall_length",
        "old_value": 4800,
        "new_value": 4900
    },
    "context": {
        "car_type": "sedan",
        "current_step": "design"
    }
}
```

### 6.2 行为类型

| 类型 | 描述 |
|------|------|
| parameter_change | 参数调整 |
| component_select | 部件选择 |
| generate_car | 车身生成 |
| quality_check | 质量检查 |
| export_model | 模型导出 |
| color_change | 颜色更改 |

## 7. 数据集统计

### 7.1 数据集规模

| 数据集 | 样本数 | 数据大小 | 更新频率 |
|--------|--------|----------|----------|
| 参数数据集 | 10,000+ | 50MB | 每周 |
| 质量数据集 | 5,000+ | 200MB | 每月 |
| 风格数据集 | 2,000+ | 1GB | 每季度 |
| 行为数据集 | 100,000+ | 100MB | 实时 |

### 7.2 数据分布

| 车型类型 | 占比 |
|----------|------|
| Sedan | 35% |
| SUV | 30% |
| Coupe | 20% |
| Hatchback | 15% |

## 8. 数据预处理

### 8.1 数据清洗

- 去除异常值和无效数据
- 处理缺失值（插值或删除）
- 标准化数据格式

### 8.2 数据增强

- 参数空间插值生成新样本
- 添加高斯噪声增强鲁棒性
- 随机参数组合生成合成数据

### 8.3 数据标准化

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
scaled_data = scaler.fit_transform(raw_data)
```

## 9. 模型训练

### 9.1 模型架构

#### 9.1.1 参数预测模型

```python
import torch
import torch.nn as nn

class ParameterPredictor(nn.Module):
    def __init__(self, input_dim=12, output_dim=12, hidden_dim=256):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )
    
    def forward(self, x):
        return self.model(x)
```

#### 9.1.2 质量评估模型

```python
class QualityEvaluator(nn.Module):
    def __init__(self, input_dim=20, output_dim=5):
        super().__init__()
        self.conv_layers = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=3),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=3),
            nn.ReLU(),
            nn.MaxPool1d(2)
        )
        self.fc_layers = nn.Sequential(
            nn.Linear(64 * 4, 128),
            nn.ReLU(),
            nn.Linear(128, output_dim),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.conv_layers(x)
        x = x.flatten(1)
        return self.fc_layers(x)
```

#### 9.1.3 风格分类模型

```python
class StyleClassifier(nn.Module):
    def __init__(self, input_dim=6, num_classes=4):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes),
            nn.Softmax(dim=1)
        )
    
    def forward(self, x):
        return self.model(x)
```

### 9.2 训练配置

| 参数 | 值 |
|------|-----|
| 学习率 | 0.001 |
| 批次大小 | 64 |
| 训练轮数 | 100 |
| 优化器 | Adam |
| 损失函数 | MSE（回归）/ CrossEntropy（分类） |
| 验证频率 | 每5轮 |
| 早停耐心 | 10轮 |

### 9.3 训练流程

```
1. 数据加载
   ↓
2. 数据预处理（标准化、增强）
   ↓
3. 划分训练/验证/测试集
   ↓
4. 模型初始化
   ↓
5. 训练循环
   ↓
6. 验证评估
   ↓
7. 模型保存
   ↓
8. 测试评估
```

## 10. 模型评估

### 10.1 评估指标

| 任务类型 | 评估指标 |
|----------|----------|
| 参数预测 | RMSE, MAE, R² |
| 质量评估 | Accuracy, F1-Score |
| 风格分类 | Accuracy, Confusion Matrix |

### 10.2 评估结果

| 模型 | 指标 | 训练集 | 验证集 | 测试集 |
|------|------|--------|--------|--------|
| 参数预测 | RMSE | 50 | 55 | 60 |
| 参数预测 | R² | 0.95 | 0.93 | 0.92 |
| 质量评估 | Accuracy | 98% | 95% | 94% |
| 风格分类 | Accuracy | 96% | 92% | 91% |

## 11. 模型部署

### 11.1 模型导出

```python
# PyTorch模型导出为ONNX
torch.onnx.export(model, dummy_input, "model.onnx", opset_version=11)

# 或保存为TorchScript
torch.jit.save(torch.jit.trace(model, dummy_input), "model.pt")
```

### 11.2 推理服务

```python
# FastAPI推理接口
from fastapi import FastAPI
import torch

app = FastAPI()
model = torch.jit.load("model.pt")

@app.post("/predict")
async def predict(params: dict):
    input_tensor = torch.tensor(list(params.values()), dtype=torch.float32)
    output = model(input_tensor)
    return {"predicted": output.tolist()}
```

## 12. 数据安全

### 12.1 数据加密

- 传输加密：HTTPS/TLS
- 存储加密：AES-256
- 敏感数据脱敏处理

### 12.2 访问控制

- 用户认证：JWT Token
- 权限管理：角色权限控制
- 数据隔离：项目级数据隔离

### 12.3 合规性

- GDPR合规
- 数据隐私保护
- 用户同意机制

## 13. 未来规划

### 13.1 数据扩展

- 增加更多车型数据
- 收集用户反馈数据
- 整合行业标准数据

### 13.2 模型升级

- 引入Transformer架构
- 实现生成式设计模型
- 开发多模态学习模型

### 13.3 功能增强

- 智能参数推荐
- 设计风格迁移
- 自动化质量优化