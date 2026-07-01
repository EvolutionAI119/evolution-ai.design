# EVOLUTION AI - Changelog

All notable changes to this project will be documented in this file.

---

## [1.1.0] - 2026-07-01

### Added - 构建参数持久化改造

- **database.py**: `ModelFile` 新增 `params_json` 字段（构建参数JSON持久化）和 `car_data_json` 字段（车身数据持久化）
- **database.py**: 新增 `ModelVariant` 表，替代内存 `_variant_store`，支持变体数据持久化存储
- **variant_routes.py**: 移除内存 `_variant_store` 和 `_version_counter`，全部改为数据库读写
  - `create_variant` — 变体数据写入 DB
  - `list_variants` — 从 DB 查询变体列表
  - `get_variant` — 从 DB 读取变体详情
  - `delete_variant` — 从 DB 删除变体记录
  - `get_version_history` — 版本历史从 DB 读取
  - `rollback_to_variant` — 回滚时更新模型 `params_json`
  - `compare_models` — 参数对比优先从 DB `params_json` 读取
- **build_routes.py**: 移除内存 `_build_cache`，构建数据持久化到 DB
  - `build_model` — 构建时保存 `params_json` 和 `car_data_json` 到 DB
  - `rebuild_model` — 重建时更新 `params_json` 和 `car_data_json`
  - `batch_build` — 批量构建结果持久化
  - `get_build_status` — 从 DB 读取构建状态
  - `get_build_cache` / `clear_build_cache` — 从 DB 查询/清除缓存
- **migrate_db.py**: 新增数据库迁移脚本（ALTER TABLE + CREATE TABLE）
- **.gitignore**: 新增排除规则（fbx/mp4/zip/pptx/pdf 等大文件）

### Fixed

- 修复服务重启后变体数据和构建缓存丢失的问题
- 修复变体 ID 计数器重启后从零开始的问题

### Tests

- **test_variant_routes.py**: 新增 3 个数据库持久化验证用例
  - `test_create_variant_persisted_to_db` — 验证变体写入 DB
  - `test_delete_variant_db_removed` — 验证删除后 DB 记录移除
  - `test_rollback_updates_model_params` — 验证回滚后 params_json 更新
- **test_build_routes.py**: 新增 6 个数据库持久化验证用例
  - 验证构建参数写入 DB、重建更新 DB、缓存查询等

### Commit Details

| Commit | Date | Description |
|--------|------|-------------|
| `216ae26` | 2026-07-01 | feat: complete DB persistence for build params and variants |
| `4d121ad` | 2026-07-01 | feat: add full EVOLUTION_AI project source code |

---

## [1.0.0] - 2026-07-01

### Added - 项目初始版本

#### Backend (FastAPI)

- **核心框架**: FastAPI + SQLAlchemy ORM + SQLite 数据库
- **API 文档**: Swagger (/docs) 和 ReDoc (/redoc)
- **数据模型**: Project / ModelFile / Workflow / WorkflowStep / QualityReport / ParameterSet

#### API 路由 (20 个接口)

- **car_routes.py** (6 接口): 车身生成、部件生成、参数预设、批量生成
- **build_routes.py** (6 接口): 模型构建、重建、批量构建、缓存管理、构建状态
- **export_routes.py** (4 接口): 多格式导出（GLB/GLTF/STL/OBJ/STEP/IGES/JSON）、导出历史
- **variant_routes.py** (7 接口): 变体创建/列表/详情/删除、版本历史、模型对比、回滚
- **modify_routes.py**: 参数化修改接口
- **routes.py**: 基础 CRUD 接口
- **learning_routes.py**: 学习引擎接口

#### 3D 模型生成

- **car_body_generator.py**: NURBS 车身生成器
  - `generate_complete_car()` — 完整车身生成
  - `generate_hood()` / `generate_windshield()` / `generate_roof()` / `generate_bumper_front()` — 部件生成
  - `export_glb()` / `export_stl()` / `export_obj()` — 网格格式导出（trimesh）
  - `export_step()` — STEP AP214 格式导出
  - `_build_trimesh_scene()` — 从 NURBS 点云构建 3D 场景
- **nurbs_engine.py**: NURBS 曲面计算引擎
- **parameterization.py**: 参数化建模
- **quality_checker.py**: 质量检查
- **topology_optimizer.py**: 拓扑优化
- **parametric_modifier.py**: 参数化修改器
- **sketch_editor.py**: 草图编辑
- **data_handover.py**: 数据交接
- **measurement_tool.py**: 测量工具

#### Frontend (Vue 3 + Element Plus)

- **页面**: Dashboard / Projects / ProjectDetail / Parameters / Workflow / Quality / Reports / Models / Handover / Modify / Demo
- **Designer** (/designer): 参数配置 + 3D 预览
- **Export** (/export): 多格式模型导出
- **Variants** (/variants): 变体管理与对比
- **api.js**: 4 个 API 模块（carAPI / buildAPI / exportAPI / variantAPI），共 26 个接口方法
- **Vite 代理**: /api -> http://localhost:8000

#### 测试 (124 用例，覆盖率 95%+)

- **test_car_routes.py**: 20 用例
- **test_build_routes.py**: 20 用例（含 6 个持久化验证）
- **test_export_routes.py**: 15 用例
- **test_variant_routes.py**: 28 用例（含 3 个持久化验证）
- **test_api.py**: 基础 API 测试
- **test_parametric_modify.py**: 参数化修改测试

#### 文档与脚本

- **docs/**: 架构设计、方法论 2.0、算法总结、五阶段流程图
- **scripts/**: 自动学习引擎、Excel 报告导出、流程图生成、算法测试
- **3d_automation/**: AI 优化 A 面工作流、拓扑优化自动化、数据交接自动化

### Fixed

- modify_routes.py NameError: `Query` 未导入
- car_body_generator.py 配置路径错误: `../config/` -> `../../config/`
- variant_routes.py 路由顺序冲突: `/{model_id}/history` 移到 `/{model_id}/{variant_id}` 之前
- GLB 导出 0 bytes: 改用 CarBodyGenerator.export_glb() 生成真实网格
- STEP 导出占位文本: 改用 CarBodyGenerator.export_step() 生成 AP214 格式
- 前端变体对比字段名: model_a/model_b -> model_id_a/model_id_b
- 前端对比结果展示: 适配 param_differences dict 格式

---

> Generated on 2026-07-01
