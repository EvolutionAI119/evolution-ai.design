# Evolution-Ai.Design

基于NURBS引擎的汽车A级曲面开发全流程解决方案。

## 功能特性

- **NURBS曲面引擎**：自研De Boor-Cox递推公式实现B样条基函数
- **参数化车身生成**：14个硬点参数驱动车身设计，支持6种车型
- **多格式导出**：GLB/STL/OBJ/STEP(AP214)/IGES
- **质量检查**：斑马纹分析、高光分析、曲率分析
- **工程数据交付**：支持多种精度级别

## 技术栈

### 前端
- Vue 3 + Vite
- Element Plus UI组件库
- Three.js 3D渲染
- Pinia 状态管理
- Vue Router 路由
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

## 项目结构

```
Evolution-Ai.Design/
├── src/                    # 前端源码
│   ├── components/         # Vue组件
│   ├── views/              # 页面视图
│   ├── config/             # 配置文件
│   ├── api.js              # API封装
│   ├── router.js           # 路由配置
│   └── main.js             # 入口文件
├── backend/                # 后端服务
│   ├── app/                # FastAPI应用
│   │   ├── routes/         # API路由
│   │   ├── nurbs.py        # NURBS引擎
│   │   ├── car_generator.py # 车身生成器
│   │   └── database.py     # 数据库ORM
│   ├── tests/              # 单元测试
│   └── start.py            # 启动脚本
├── public/                 # 静态资源
├── dist/                   # 构建产物
└── package.json            # 前端依赖配置
```

## API接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v1/car/generate` | POST | 生成完整车身 |
| `/api/v1/car/components` | GET | 获取部件列表 |
| `/api/v1/car/parameters` | GET | 获取参数配置 |
| `/api/v1/quality/check` | POST | 质量检查 |
| `/api/v1/export/` | POST | 模型导出 |
| `/api/v1/export/formats` | GET | 支持的导出格式 |

## 部署

### GitHub Pages

```bash
# 构建前端
npm run build

# 部署到gh-pages分支
git subtree push --prefix dist origin gh-pages
```

### 自定义域名

在 `dist/CNAME` 文件中配置域名：
```
evolution-ai.design
```

## 许可证

MIT License