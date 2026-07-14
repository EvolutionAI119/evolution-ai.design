# Evolution-Ai.Design

基于NURBS引擎的汽车A级曲面开发全流程解决方案。

## 设计哲学

**EVOLUTION AI 汽车造型设计哲学**

*Where Ancient Wisdom Meets Modern Engineering*

### 范式跃迁

| 对比维度 | 传统CAD | EVOLUTION AI |
|----------|---------|--------------|
| 设计起点 | 几何线条 | 物理硬点 |
| 驱动方式 | 主观拖拽 | 参数约束 |
| 曲面质量 | 人工雕琢 | 全局优化 |
| 迭代效率 | 周级 | 秒级 |

### 四大架构

1. **美学造型层**：形态拓扑、美学原则、风格识别
2. **特征语言层**：线条定义、表面特征、细节刻画
3. **曲面工程层**：NURBS曲面、G2连续性、A级曲面
4. **参数空间层**：参数化驱动、约束求解、优化算法

### 形-理-数三角架构

- **形（Form）**：车身造型的外在形态和美学表现
- **理（Logic）**：设计逻辑和工程约束
- **数（Math）**：数学建模和参数化表达

### 哲学根基

| 哲学概念 | 西方源头 | 设计映射 |
|----------|----------|----------|
| 理念原型 | 柏拉图理念论 | 设计参数→形态参数→曲面表达 |
| 因果律 | 亚里士多德物理学 | 特征约束→曲面约束→工程约束 |
| 生成 | 康德先验美学 | 参数→形态→曲面 |
| 演化 | 达尔文进化论 | 变异→适应→自然选择 |

### 文化观念-造型语言转译

| 东方哲学观念 | 造型语言转译 |
|--------------|--------------|
| 天人合一 | 车身线条与自然流畅融合 |
| 大象无形 | 极简主义设计，追求本质形态 |
| 气韵生动 | 车身线条富有节奏感和生命力 |
| 中和之美 | 各设计元素间的平衡与和谐 |

### 品牌基因与工程效果

- **Rolls-Royce**：帕特农神庙式格栅、欢庆女神立标、尊贵典雅
- **Bentley**：矩阵式格栅、圆形大灯、豪华运动风格
- **Bugatti**：马蹄形格栅、C型侧线、极致空气动力学
- **Porsche**：蛙眼大灯、溜背造型、德系精密工程美学
- **Ferrari**：跃马标志、空气动力学雕塑、意大利超跑灵魂

### 核心理念

> "从观察中提炼规律，在约束中生成形态，于曲面中转化为工程实现。"
>
> "将文明的智慧基因，转化为面向未来的工程实践能力。"
>
> "外化于形，内化于中。"

## 功能特性

- **NURBS曲面引擎**：自研De Boor-Cox递推公式实现B样条基函数
- **参数化车身生成**：14个硬点参数驱动车身设计，生成34个部件、15+ NURBS曲面、776+控制点
- **多格式导出**：GLB/STL/OBJ/STEP(AP214)/IGES
- **质量检查**：斑马纹分析、高光分析、曲率分析、G0/G1/G2连续性检查
- **工程数据交付**：支持多种精度级别
- **AI辅助设计**：智能参数推荐、设计风格识别

## 技术栈

### 前端
- Vue 3 + Vite
- Element Plus UI组件库
- Three.js 3D渲染
- Pinia 状态管理
- Vue Router 路由
- Vue I18n 国际化
- Axios HTTP客户端

### 后端
- FastAPI
- SQLAlchemy ORM
- SQLite数据库
- NURBS引擎（自研）
- numpy / trimesh

## 快速开始

### 环境要求
- Node.js >= 18
- Python >= 3.10

### 安装依赖

```bash
# 前端依赖
npm install

# 后端依赖
cd backend
pip install -r requirements.txt
```

### 启动服务

```bash
# 启动后端服务（端口8000）
cd backend
python start.py

# 启动前端开发服务器（端口3000）
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 本地预览

```bash
# 使用HTTP服务器预览（推荐）
cd dist
python -m http.server 8080
# 访问 http://localhost:8080

# 或使用启动脚本
start.bat  # Windows
```

## 项目结构

```
Evolution-Ai.Design/
├── src/                    # 前端源码
│   ├── components/         # Vue组件
│   ├── views/              # 页面视图
│   ├── store/              # Pinia状态管理
│   ├── api.js              # API封装
│   ├── router.js           # 路由配置
│   ├── i18n.js             # 国际化配置
│   └── main.js             # 入口文件
├── backend/                # 后端服务
│   ├── app/                # FastAPI应用
│   │   ├── routes/         # API路由
│   │   ├── nurbs.py        # NURBS引擎
│   │   ├── car_generator.py # 车身生成器
│   │   ├── database.py     # 数据库ORM
│   │   ├── schemas.py      # 数据模型
│   │   ├── config.py       # 配置文件
│   │   └── main.py         # 应用入口
│   ├── config/             # 配置文件
│   ├── tests/              # 单元测试
│   └── start.py            # 启动脚本
├── docs/                   # 技术文档
│   ├── algorithms/         # 算法文档
│   ├── api/                # API文档
│   ├── deployment/         # 部署文档
│   ├── product/            # 产品文档
│   ├── development/        # 开发文档
│   ├── deeplearning/       # 深度学习文档
│   └── patents/            # 专利文档
├── public/                 # 静态资源
├── dist/                   # 构建产物
├── start.bat               # 启动脚本
├── CNAME                   # GitHub Pages域名配置
└── package.json            # 前端依赖配置
```

## 技术文档

| 文档 | 路径 | 说明 |
|------|------|------|
| NURBS引擎算法 | docs/algorithms/nurbs_engine.md | B样条基函数、De Boor-Cox递推 |
| 车身生成算法 | docs/algorithms/car_body_generator.md | 34个部件生成、硬点参数系统 |
| API接口文档 | docs/api/api_reference.md | RESTful API定义、调用示例 |
| Docker配置 | docs/deployment/docker_config.md | 容器化部署、环境配置 |
| 产品定义 | docs/product/product_definition.md | 产品定位、功能规格 |
| 开发过程 | docs/development/development_process.md | 开发流程、测试报告 |
| 深度学习训练集 | docs/deeplearning/training_dataset.md | 数据集架构、模型训练 |
| 专利文档 | docs/patents/patent_document.md | 专利申请、技术保护 |
| 方法论论文 | docs/development/methodology_paper.md | 产品开发方法论 |
| 设计哲学 | docs/design_philosophy.md | 汽车造型设计哲学体系 |

## API接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/car/generate` | POST | 生成完整车身 |
| `/api/v1/car/generate/component` | POST | 生成单个部件 |
| `/api/v1/car/components` | GET | 获取部件列表 |
| `/api/v1/car/parameters` | GET | 获取参数配置 |
| `/api/v1/car/regenerate` | POST | 重新生成车身 |
| `/api/v1/quality/check/` | POST | 质量检查 |
| `/api/v1/quality/reports/` | GET | 获取质量报告列表 |
| `/api/v1/quality/topology/optimize/` | POST | 拓扑优化 |
| `/api/v1/export/` | POST | 模型导出 |
| `/api/v1/export/download/{model_id}/{format}` | GET | 下载导出文件 |
| `/api/v1/export/formats` | GET | 支持的导出格式 |
| `/api/v1/projects/` | CRUD | 项目管理 |
| `/api/v1/models/` | CRUD | 模型管理 |

## 部署

### GitHub Pages

```bash
# 构建前端
npm run build

# 部署到gh-pages分支
git subtree push --prefix dist origin gh-pages
```

### Docker部署

```bash
# 构建并启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 自定义域名

在 `dist/CNAME` 文件中配置域名：
```
evolution-ai.design
```

## 许可证

MIT License

## 联系方式

- 项目地址：https://github.com/EvolutionAI119/evolution-ai.design
- 网站：https://evolution-ai.design