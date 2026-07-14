# EVOLUTION AI API接口文档

## 1. 概述

EVOLUTION AI提供完整的RESTful API接口，支持车身生成、质量检查、模型导出等功能。

**基础URL**: `http://localhost:8000/api/v1`

**认证方式**: 暂无（预留JWT认证接口）

## 2. 接口列表

### 2.1 健康检查

```
GET /api/v1/health
```

**响应**:
```json
{
    "status": "healthy",
    "service": "EVOLUTION AI"
}
```

### 2.2 车身生成接口

#### 2.2.1 生成完整车身

```
POST /api/v1/car/generate
```

**请求体**:
```json
{
    "car_type": "sedan",
    "params": {
        "overall_length": 4800,
        "overall_width": 1900,
        "overall_height": 1450,
        "wheelbase": 2850
    },
    "color": "#c0c0c0"
}
```

**响应**:
```json
{
    "name": "完整车身",
    "components": [...],
    "total_surfaces": 34,
    "parameters": {...}
}
```

#### 2.2.2 生成单个部件

```
POST /api/v1/car/generate/component
```

**请求体**:
```json
{
    "component": "hood",
    "side": "left",
    "position": "front",
    "pillar_type": "A"
}
```

**支持的部件**:

| 部件 | 参数要求 |
|------|----------|
| hood, windshield, roof, rear_window, trunk | 无 |
| bumper_front, bumper_rear, grille, door_seam | 无 |
| door_front, door_rear, headlight, taillight, mirror | side |
| wheel, fender | side, position |
| pillar | side, pillar_type |

#### 2.2.3 列出所有部件

```
GET /api/v1/car/components
```

**响应**:
```json
{
    "components": [
        {"component": "hood", "params": []},
        {"component": "door_front", "params": ["side"]},
        {"component": "wheel", "params": ["side", "position"]}
    ],
    "total": 20
}
```

#### 2.2.4 获取参数配置

```
GET /api/v1/car/parameters
```

#### 2.2.5 重新生成车身

```
POST /api/v1/car/regenerate
```

### 2.3 质量检查接口

#### 2.3.1 质量检查

```
POST /api/v1/quality/check/
```

**请求体**:
```json
{
    "model_id": 1,
    "checks": ["zebra", "highlight", "curvature"]
}
```

**响应**:
```json
{
    "score": 92.5,
    "passed": true,
    "checks": {
        "continuity_g0": true,
        "continuity_g1": true,
        "continuity_g2": true,
        "curvature_quality": 0.95,
        "surface_smoothness": 0.88
    },
    "issues": [],
    "report_id": 1,
    "timestamp": "2026-07-14T10:00:00"
}
```

#### 2.3.2 获取质量报告列表

```
GET /api/v1/quality/reports/?project_id=1&model_id=1
```

#### 2.3.3 获取单个质量报告

```
GET /api/v1/quality/reports/{report_id}
```

#### 2.3.4 拓扑优化

```
POST /api/v1/quality/topology/optimize/
```

**请求体**:
```json
{
    "model_id": 1,
    "target_faces": 10000,
    "min_quad_ratio": 0.8
}
```

### 2.4 模型导出接口

#### 2.4.1 导出模型

```
POST /api/v1/export/
```

**请求体**:
```json
{
    "model_id": 1,
    "formats": ["glb", "stl", "obj", "step"],
    "precision": 0.1
}
```

**支持的格式**:

| 格式 | 扩展名 | MIME类型 | 说明 |
|------|--------|----------|------|
| glb | .glb | model/gltf-binary | GLTF二进制 |
| gltf | .gltf | model/gltf+json | GLTF JSON |
| stl | .stl | model/stl | STL网格 |
| obj | .obj | model/obj | Wavefront OBJ |
| step | .step | model/step | STEP工程 |
| stp | .stp | model/step | STEP别名 |
| iges | .iges | model/iges | IGES格式 |
| igs | .igs | model/iges | IGES别名 |
| json | .json | application/json | JSON数据 |

**响应**:
```json
{
    "model_id": 1,
    "files": [
        {"format": "glb", "filename": "model_1.glb", "path": "...", "size": 40960, "mime_type": "model/gltf-binary"}
    ],
    "export_time_ms": 125.5
}
```

#### 2.4.2 下载导出文件

```
GET /api/v1/export/download/{model_id}/{format}
```

#### 2.4.3 列出支持的格式

```
GET /api/v1/export/formats
```

#### 2.4.4 获取导出历史

```
GET /api/v1/export/history/{model_id}
```

### 2.5 项目管理接口

```
POST /api/v1/projects/          # 创建项目
GET /api/v1/projects/           # 获取项目列表
GET /api/v1/projects/{id}       # 获取项目详情
PUT /api/v1/projects/{id}       # 更新项目
DELETE /api/v1/projects/{id}    # 删除项目
```

### 2.6 模型管理接口

```
POST /api/v1/models/            # 创建模型
GET /api/v1/models/             # 获取模型列表
GET /api/v1/models/{id}         # 获取模型详情
PUT /api/v1/models/{id}         # 更新模型
DELETE /api/v1/models/{id}      # 删除模型
```

### 2.7 工作流接口

```
POST /api/v1/workflow/start/    # 启动工作流
GET /api/v1/workflow/status/    # 获取工作流状态
POST /api/v1/workflow/stop/     # 停止工作流
```

### 2.8 模型变体接口

```
POST /api/v1/variant/generate/  # 生成模型变体
GET /api/v1/variant/list/       # 获取变体列表
```

### 2.9 模型修改接口

```
POST /api/v1/modify/deform/     # 变形修改
POST /api/v1/modify/smooth/     # 平滑处理
POST /api/v1/modify/trim/       # 修剪操作
```

## 3. 错误响应格式

```json
{
    "detail": "Error message here"
}
```

**HTTP状态码**:

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

## 4. 前端API封装

前端通过 `api.js` 封装所有接口调用：

```javascript
import axios from 'axios'

const api = axios.create({
    baseURL: '/api/v1',
    timeout: 30000
})

export const carAPI = {
    generate: (data) => api.post('/car/generate', data),
    generateComponent: (component, data) => api.post('/car/generate/component', { component, ...data }),
    getComponents: () => api.get('/car/components'),
    getParameters: () => api.get('/car/parameters'),
    regenerate: (data) => api.post('/car/regenerate', data),
    export: (data) => api.post('/car/export', data)
}

export const qualityAPI = {
    check: (data) => api.post('/quality/check/', data),
    getReports: (params) => api.get('/quality/reports/', { params }),
    getReport: (id) => api.get(`/quality/reports/${id}`),
    optimize: (data) => api.post('/quality/topology/optimize/', data)
}

export const exportAPI = {
    exportModel: (data) => api.post('/export/', data),
    download: (modelId, format) => api.get(`/export/download/${modelId}/${format}`),
    getFormats: () => api.get('/export/formats'),
    getHistory: (modelId) => api.get(`/export/history/${modelId}`)
}
```

## 5. WebSocket接口（预留）

```
ws://localhost:8000/ws/
```

**消息格式**:
```json
{
    "type": "progress",
    "data": {
        "task": "generate",
        "progress": 50,
        "message": "Generating hood..."
    }
}
```

## 6. 接口调用示例

### 6.1 使用curl

```bash
# 生成完整车身
curl -X POST http://localhost:8000/api/v1/car/generate \
  -H "Content-Type: application/json" \
  -d '{"car_type": "sedan", "color": "#c0c0c0"}'

# 质量检查
curl -X POST http://localhost:8000/api/v1/quality/check/ \
  -H "Content-Type: application/json" \
  -d '{"model_id": 1, "checks": ["zebra", "curvature"]}'

# 导出模型
curl -X POST http://localhost:8000/api/v1/export/ \
  -H "Content-Type: application/json" \
  -d '{"model_id": 1, "formats": ["glb", "stl"]}'
```

### 6.2 使用Python

```python
import requests

# 生成车身
response = requests.post('http://localhost:8000/api/v1/car/generate', json={
    'car_type': 'sedan',
    'color': '#c0c0c0'
})
print(response.json())

# 质量检查
response = requests.post('http://localhost:8000/api/v1/quality/check/', json={
    'model_id': 1,
    'checks': ['zebra', 'curvature']
})
print(response.json())
```