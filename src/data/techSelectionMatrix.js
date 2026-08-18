export const techSelectionMatrix = [
  {
    id: 1,
    dimension: "大模型基座",
    currentSolution: "无",
    recommendedSolution: "DeepSeek 私有化",
    stage: "短期",
    priority: "P0",
    coreReason: "中文推理强 + 可私有化部署，符合数据安全要求",
    candidates: [
      {
        name: "DeepSeek",
        scores: { semanticUnderstanding: 5, industryKnowledge: 4, deployment: 5, inferenceCost: 5, chineseSupport: 5, functionCalling: 4 },
        deploymentMode: "本地私有化",
        note: "白皮书推荐基座，中文推理能力突出"
      },
      {
        name: "Qwen 通义千问",
        scores: { semanticUnderstanding: 4, industryKnowledge: 4, deployment: 4, inferenceCost: 4, chineseSupport: 5, functionCalling: 4 },
        deploymentMode: "云端API/本地",
        note: "开源生态好，阿里云生态集成便利"
      },
      {
        name: "文心一言",
        scores: { semanticUnderstanding: 4, industryKnowledge: 3, deployment: 3, inferenceCost: 3, chineseSupport: 5, functionCalling: 3 },
        deploymentMode: "云端API",
        note: "与阿尔特御风风阻AI同源，行业契合度高"
      },
      {
        name: "自研垂域小模型",
        scores: { semanticUnderstanding: 3, industryKnowledge: 5, deployment: 5, inferenceCost: 4, chineseSupport: 4, functionCalling: 3 },
        deploymentMode: "本地",
        note: "基于Llama微调，可控性强但研发周期长"
      }
    ],
    dependencies: []
  },
  {
    id: 2,
    dimension: "几何内核",
    currentSolution: "自研 NURBS",
    recommendedSolution: "自研 + STEP 导出",
    stage: "短期",
    priority: "P0",
    coreReason: "保持核心算法优势的同时打通与主流CAD的数据流",
    candidates: [
      {
        name: "自研 NURBS 内核",
        scores: { classASurface: 4, g2Continuity: 4, stepIges: 1, licenseCost: 5, devDifficulty: 2, ecosystem: 2 },
        note: "当前方案，Python+NumPy+Cython，A级曲面能力已验证"
      },
      {
        name: "OpenCASCADE",
        scores: { classASurface: 3, g2Continuity: 3, stepIges: 5, licenseCost: 5, devDifficulty: 3, ecosystem: 4 },
        note: "开源C++工业级B-rep内核，STEP/IGES支持完善"
      },
      {
        name: "CATIA GSD/Freestyle",
        scores: { classASurface: 5, g2Continuity: 5, stepIges: 5, licenseCost: 1, devDifficulty: 1, ecosystem: 5 },
        note: "商业授权，A级曲面行业标杆，但成本高且封闭"
      },
      {
        name: "Parasolid",
        scores: { classASurface: 4, g2Continuity: 4, stepIges: 5, licenseCost: 1, devDifficulty: 2, ecosystem: 4 },
        note: "商业内核，UG/SolidWorks同源，二次开发友好度中等"
      }
    ],
    dependencies: []
  },
  {
    id: 3,
    dimension: "3D可视化与渲染",
    currentSolution: "PyVista",
    recommendedSolution: "PyVista + Three.js",
    stage: "短期",
    priority: "P1",
    coreReason: "后端做质量评估，前端做交互展示，双轨并行覆盖全场景",
    candidates: [
      {
        name: "PyVista",
        scores: { renderQuality: 3, realtimeInteraction: 2, webAccess: 1, reflectionAnalysis: 5, learningCost: 4, cloudNative: 2 },
        note: "当前方案，Python原生，适合科研验证与质量评估"
      },
      {
        name: "Three.js",
        scores: { renderQuality: 4, realtimeInteraction: 5, webAccess: 5, reflectionAnalysis: 3, learningCost: 3, cloudNative: 4 },
        note: "Web端，Evolution-Ai.Design已使用，交互体验佳"
      },
      {
        name: "Babylon.js",
        scores: { renderQuality: 5, realtimeInteraction: 5, webAccess: 5, reflectionAnalysis: 3, learningCost: 3, cloudNative: 4 },
        note: "Web端，PBR渲染能力强，游戏级体验"
      },
      {
        name: "NVIDIA Omniverse",
        scores: { renderQuality: 5, realtimeInteraction: 4, webAccess: 2, reflectionAnalysis: 4, learningCost: 1, cloudNative: 5 },
        note: "白皮书方案，云原生，影视级渲染但学习成本高"
      },
      {
        name: "Unity/Unreal",
        scores: { renderQuality: 5, realtimeInteraction: 5, webAccess: 2, reflectionAnalysis: 3, learningCost: 2, cloudNative: 3 },
        note: "游戏引擎，影视级渲染，但过重"
      }
    ],
    dependencies: []
  },
  {
    id: 4,
    dimension: "前端框架",
    currentSolution: "Streamlit + Vue 3",
    recommendedSolution: "统一 Vue 3",
    stage: "中期",
    priority: "P1",
    coreReason: "统一技术栈提升可维护性，Streamlit降级为算法调试工具",
    candidates: [
      {
        name: "Streamlit",
        scores: { devEfficiency: 5, interaction: 2, integration3D: 2, complexForm: 2, teamSkill: 4, maintainability: 2 },
        note: "Python全栈，快速原型，但复杂交互受限"
      },
      {
        name: "Vue 3 + Element Plus",
        scores: { devEfficiency: 4, interaction: 5, integration3D: 5, complexForm: 5, teamSkill: 5, maintainability: 5 },
        note: "当前Design平台方案，组件生态成熟"
      },
      {
        name: "React + Ant Design",
        scores: { devEfficiency: 4, interaction: 5, integration3D: 5, complexForm: 5, teamSkill: 3, maintainability: 5 },
        note: "生态最大，但团队当前以Vue为主"
      },
      {
        name: "Gradio",
        scores: { devEfficiency: 4, interaction: 3, integration3D: 2, complexForm: 3, teamSkill: 3, maintainability: 2 },
        note: "Python，AI应用常用，但扩展性有限"
      }
    ],
    dependencies: [3]
  },
  {
    id: 5,
    dimension: "曲面光顺优化算法",
    currentSolution: "模拟退火",
    recommendedSolution: "SA + 贝叶斯优化",
    stage: "短期",
    priority: "P1",
    coreReason: "全局搜索保证收敛，贝叶斯优化做精调提升效率",
    candidates: [
      {
        name: "模拟退火",
        scores: { globalConvergence: 5, computeCost: 3, interpretability: 4, constraintHandling: 4, initialDependency: 3, dataRequirement: 5 },
        note: "当前方案，全局搜索能力强，无需梯度"
      },
      {
        name: "遗传算法",
        scores: { globalConvergence: 5, computeCost: 2, interpretability: 3, constraintHandling: 3, initialDependency: 4, dataRequirement: 5 },
        note: "种群并行，适合多目标优化但计算量大"
      },
      {
        name: "梯度下降/变分法",
        scores: { globalConvergence: 2, computeCost: 5, interpretability: 5, constraintHandling: 3, initialDependency: 1, dataRequirement: 5 },
        note: "局部精确，需可导，对初始解敏感"
      },
      {
        name: "强化学习",
        scores: { globalConvergence: 4, computeCost: 2, interpretability: 2, constraintHandling: 4, initialDependency: 4, dataRequirement: 1 },
        note: "数据驱动，需大量样本，长期方向"
      },
      {
        name: "贝叶斯优化",
        scores: { globalConvergence: 4, computeCost: 4, interpretability: 4, constraintHandling: 4, initialDependency: 3, dataRequirement: 4 },
        note: "样本高效，适合精调阶段"
      }
    ],
    dependencies: []
  },
  {
    id: 6,
    dimension: "智能体框架",
    currentSolution: "无",
    recommendedSolution: "LangGraph",
    stage: "中期",
    priority: "P0",
    coreReason: "单Agent闭环成熟，预留接入行业平台接口",
    candidates: [
      {
        name: "LangChain/LangGraph",
        scores: { multiAgent: 4, toolCalling: 5, taskPlanning: 4, observability: 4, industryIntegration: 3, learningCurve: 3 },
        note: "生态最全，工具调用成熟，LangGraph支持图式编排"
      },
      {
        name: "Microsoft AutoGen",
        scores: { multiAgent: 5, toolCalling: 4, taskPlanning: 4, observability: 3, industryIntegration: 2, learningCurve: 3 },
        note: "多Agent对话强，微软生态"
      },
      {
        name: "阿尔特AI+数智创造平台",
        scores: { multiAgent: 4, toolCalling: 3, taskPlanning: 4, observability: 2, industryIntegration: 5, learningCurve: 2 },
        note: "行业平台，接入即协同，但依赖外部"
      },
      {
        name: "自研轻量框架",
        scores: { multiAgent: 2, toolCalling: 3, taskPlanning: 3, observability: 4, industryIntegration: 3, learningCurve: 4 },
        note: "可控性强，但重复造轮子"
      }
    ],
    dependencies: [1]
  },
  {
    id: 7,
    dimension: "部署架构",
    currentSolution: "本地 Docker",
    recommendedSolution: "混合云",
    stage: "中期",
    priority: "P1",
    coreReason: "数据安全与算力弹性的平衡，核心算法本地，大模型上云",
    candidates: [
      {
        name: "本地 Docker",
        scores: { computeElasticity: 1, dataSecurity: 5, opsCost: 3, llmAccess: 1, multiUser: 1 },
        note: "当前方案，1.49GB单节点，数据安全好"
      },
      {
        name: "云原生 K8s",
        scores: { computeElasticity: 5, dataSecurity: 2, opsCost: 2, llmAccess: 5, multiUser: 5 },
        note: "弹性算力，白皮书方向，但车型数据敏感"
      },
      {
        name: "混合云",
        scores: { computeElasticity: 4, dataSecurity: 4, opsCost: 3, llmAccess: 4, multiUser: 4 },
        note: "核心算法与数据本地，大模型/渲染上云"
      },
      {
        name: "边缘+云协同",
        scores: { computeElasticity: 3, dataSecurity: 4, opsCost: 2, llmAccess: 3, multiUser: 3 },
        note: "低延迟场景，但架构复杂"
      }
    ],
    dependencies: [1, 6]
  },
  {
    id: 8,
    dimension: "数据存储与知识管理",
    currentSolution: "无",
    recommendedSolution: "PG + Milvus + Neo4j",
    stage: "中期",
    priority: "P2",
    coreReason: "三层数据飞轮基础：结构化参数 + 语义检索 + 知识关联",
    candidates: [
      {
        name: "PostgreSQL",
        scores: { paramStorage: 5, knowledgeRetrieval: 3, brandDna: 3, scalability: 4, ragIntegration: 3 },
        note: "关系型，结构化设计参数存储"
      },
      {
        name: "Milvus/Pinecone",
        scores: { paramStorage: 2, knowledgeRetrieval: 5, brandDna: 3, scalability: 5, ragIntegration: 5 },
        note: "向量数据库，语义检索，RAG核心组件"
      },
      {
        name: "Neo4j",
        scores: { paramStorage: 2, knowledgeRetrieval: 4, brandDna: 5, scalability: 3, ragIntegration: 4 },
        note: "知识图谱，造型特征关联与品牌DNA建模"
      },
      {
        name: "MinIO",
        scores: { paramStorage: 3, knowledgeRetrieval: 1, brandDna: 1, scalability: 5, ragIntegration: 2 },
        note: "对象存储，模型文件与资产存储"
      }
    ],
    dependencies: [1, 6]
  }
]

export const matrixMetadata = {
  title: "技术选型决策矩阵",
  scoreScale: {
    min: 1,
    max: 5,
    labels: {
      1: "差",
      2: "较弱",
      3: "中等",
      4: "良好",
      5: "优秀"
    }
  },
  priorityLabels: {
    P0: "最高优先级 - 阻塞型，必须先解决",
    P1: "高优先级 - 影响核心能力",
    P2: "中优先级 - 长期基础设施建设"
  },
  stageLabels: {
    "短期": "1-3个月",
    "中期": "3-6个月",
    "长期": "6个月以上"
  },
  dependencyNote: "dependencies 字段表示该选型依赖的其他选型ID，需按顺序决策"
}
