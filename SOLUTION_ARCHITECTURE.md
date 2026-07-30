# EVOLUTION AI · 汽车A面设计系统
## Automotive Class A Surface AI Generation System

---

## 一、项目愿景

**目标**：打造 AI 时代汽车造型 A 级曲面数字模型设计系统

### 核心能力
1. **NURBS 曲面生成** — 基于算法驱动的 B 样条/NURBS 曲面构造
2. **A 级曲面验证** — G1/G2 连续性检测、曲率分析、反射质量评估
3. **参数化零部件设计** — 车身、内外饰零部件的参数化生成
4. **整车装配系统** — 多零部件协同装配、公差分析
5. **AI 驱动的形态进化** — 生成→评估→优化循环

### 核心技术栈
- **几何内核**：纯 Python NURBS 实现（自主知识产权）
- **AI 模型**：多任务神经网络（曲面质量预测 + 形态生成）
- **训练框架**：PyTorch + 自定义几何损失函数
- **可视化**：Three.js / PyThree.js / WebGL 实时预览

---

## 二、系统架构

```
EVOLUTION_AI/
├── core/                          # 核心引擎
│   ├── nurbs/                     # NURBS 数学引擎
│   │   ├── curve.py               # NURBS 曲线
│   │   ├── surface.py              # NURBS 曲面
│   │   ├── continuity.py           # G0/G1/G2 连续性
│   │   ├── matching.py             # 曲面拼接匹配
│   │   └── subdivision.py          # 曲面细分
│   ├── cad/                        # CAD 操作
│   │   ├── part.py                 # 零件描述
│   │   ├── assembly.py             # 装配体
│   │   ├── feature.py             # 特征操作（倒角/拔模/孔）
│   │   └── booleans.py            # 布尔运算
│   ├── class_a/                   # A级曲面评估
│   │   ├── curvature.py            # 曲率分析
│   │   ├── reflection.py           # 反射线分析
│   │   ├── discontinuity.py       # 不连续性检测
│   │   ├── quality_score.py       # 综合质量评分
│   │   └── report.py              # 评估报告
│   └── geometry/                  # 基础几何
│       ├── vector.py              # 向量/矩阵
│       ├── transform.py           # 变换矩阵
│       ├── bsp.py                 # B-样条基函数
│       └── solvers.py             # 数值求解器
│
├── generation/                    # 生成模块
│   ├── parametric/               # 参数化设计
│   │   ├── body.py               # 车身参数化
│   │   ├── panel.py              # 车身板件
│   │   ├── wheel.py              # 车轮设计
│   │   └── trim.py               # 内饰件
│   ├── ai_generator/             # AI 生成器
│   │   ├── surf_vla.py           # 曲面 VLA 模型
│   │   ├── surf_vae.py           # 曲面 VAE 模型
│   │   ├── morphology.py          # 形态学变换
│   │   └── constraints.py        # 约束满足
│   └── evolve/                   # 进化优化
│       ├── ga_optimizer.py       # 遗传算法
│       ├── cmaes.py              # CMA-ES
│       └── bayesian.py           # 贝叶斯优化
│
├── training/                     # 训练管线
│   ├── datasets/                  # 数据集
│   │   ├── automotive_curves/     # 汽车曲线数据
│   │   ├── automotive_surfaces/   # 汽车曲面数据
│   │   └── class_a_labels/       # A级标签
│   ├── data_collector.py         # 数据采集
│   ├── surf_train.py             # 曲面模型训练
│   ├── quality_train.py          # 质量预测训练
│   └── checkpoints/              # 模型快照
│
├── viewer/                       # 3D 查看器
│   ├── web_viewer/               # Web 端
│   │   ├── index.html            # 主界面
│   │   ├── three_viewer.js       # Three.js 查看器
│   │   └── nurbs_renderer.js     # NURBS 渲染器
│   └── api_server.py             # 查看器 API
│
├── knowledge/                    # 知识库
│   ├── automotive_db/            # 汽车知识图谱
│   ├── design_rules/             # 设计规则库
│   └── surface_catalog/          # 曲面分类目录
│
└── SUPER_AGENT/                  # 超级智能体编排
    ├── evo_agent.py             # EVOLUTION AI 专属 Agent
    ├── research_engine.py        # 研究引擎
    ├── code_generator.py         # 代码生成器
    └── system.py                 # 系统编排器
```

---

## 三、NURBS 数学基础

### 3.1 NURBS 曲线
```
C(u) = Σ(i=0,n) R_i,p(u) · P_i

其中:
R_i,p(u) = N_i,p(u) · w_i / Σ(j=0,n) N_j,p(u) · w_j

N_i,p(u) = B-样条基函数（de Boor 递归）
P_i      = 控制点坐标
w_i      = 权重
p        = 多项式阶数
```

### 3.2 NURBS 曲面
```
S(u,v) = Σ(i=0,n) Σ(j=0,m) R_i,j,p,q(u,v) · P_i,j

R_i,j,p,q(u,v) = N_i,p(u) · N_j,q(v) · w_i,j / Σ(k=0,n) Σ(l=0,m) N_k,p(u) · N_l,q(v) · w_k,l
```

### 3.3 连续性条件
- **G0 (位置连续)**: S1(u0) = S2(u0)
- **G1 (切向连续)**: ∂S1/∂u |u0 = λ · ∂S2/∂u |u0
- **G2 (曲率连续)**: ∂²S1/∂u² |u0 = μ · ∂²S2/∂u² |u0 + 切向修正项

### 3.4 A 级曲面标准
| 指标 | 要求 |
|------|------|
| G0 连续 | 所有面片连接处 |
| G1 连续 | 主要可见区域 |
| G2 连续 | A 级外表面（车身、顶盖、发动机罩） |
| 曲率半径 | ≥ 1mm（无尖角） |
| 高光质量 | 连续无扭曲 |
| 反射线 | 平滑无折断 |

---

## 四、AI 模型设计

### 4.1 曲面质量预测 VLA
- **输入**：NURBS 参数（控制点、权重、节点向量）
- **输出**：A/B/C 表面分级 + 具体缺陷标注
- **训练数据**：10,000+ 汽车曲面样本

### 4.2 形态生成模型
- **架构**：Transformer + 几何注意力
- **输入**：设计意图文本 + 参数约束
- **输出**：NURBS 曲面参数

### 4.3 多任务损失函数
```
L_total = λ1·L_quality + λ2·L_continuity + λ3·L_curvature + λ4·L_physics
```

---

## 五、关键算法

### 5.1 de Boor 算法（基函数递归）
```
N_i,0(u) = 1 if u_i ≤ u < u_{i+1} else 0
N_i,p(u) = (u - u_i)/(u_{i+p} - u_i) · N_i,p-1(u) 
          + (u_{i+p+1} - u)/(u_{i+p+1} - u_{i+1}) · N_{i+1},p-1(u)
```

### 5.2 曲面求交（trimming）
- Newton-Raphson 迭代
- 支撑树求交
- Bézier 裁剪

### 5.3 G2 连续性拼接
- 双切向匹配
- 曲率跳跃控制
- 小波分析检测

---

## 六、里程碑计划

| 阶段 | 内容 | 产出 |
|------|------|------|
| **Phase 1** | NURBS 核心数学引擎 | curve.py, surface.py |
| **Phase 2** | A 级曲面评估系统 | class_a/ 完整模块 |
| **Phase 3** | 参数化零部件设计 | body.py, wheel.py |
| **Phase 4** | AI 质量预测模型 | surf_vla.py + 训练 |
| **Phase 5** | 整车装配系统 | assembly.py |
| **Phase 6** | Web 3D 查看器 | viewer/ |
| **Phase 7** | SUPER_AGENT 集成 | evo_agent.py |

---

## 七、参考标准

- **ISO 10303** — STEP 文件格式
- **DIN 5321** — 汽车外表面质量
- **BMW Group Surface Standard** — BMW 设计标准
- **Tesla Surface Guidelines** — 特斯拉 A 面标准
- **OpensCAD/NaroCAD** — 开源 CAD 参考

---

*EVOLUTION_AI · AI驱动汽车造型设计 · 持续进化中*
