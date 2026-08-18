import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { carTypeParams, defaultCarParams } from '../config/carPresets'

function snakeToCamel(obj) {
  if (!obj || typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(snakeToCamel)
  const result = {}
  for (const key in obj) {
    const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
    result[camelKey] = snakeToCamel(obj[key])
  }
  return result
}

export const useDesignerStore = defineStore('designer', () => {
  const carType = ref('sedan')
  const brand = ref('rolls-royce')
  const selectedModel = ref(null)
  const selectedColor = ref('#4ade80')
  const params = ref({ ...defaultCarParams, ...carTypeParams.sedan })
  const viewMode = ref('3d')
  const isLoading = ref(false)
  const generating = ref(false)

  const currentCarTypeParams = computed(() => carTypeParams[carType.value] || {})
  
  const mergedParams = computed(() => ({
    ...defaultCarParams,
    ...currentCarTypeParams,
    ...params.value
  }))

  function setCarType(type) {
    carType.value = type
    selectedModel.value = null
    const typeParams = carTypeParams[type] || {}
    params.value = { ...defaultCarParams, ...typeParams }
  }

  function setBrand(b) {
    brand.value = b
    selectedModel.value = null
  }

  function selectModel(model) {
    selectedModel.value = model.key
    if (model.params) {
      params.value = { ...defaultCarParams, ...model.params }
    }
  }

  function selectColor(color) {
    selectedColor.value = color
  }

  function setGenerating(val) {
    generating.value = val
  }

  function updateParam(key, value) {
    params.value[key] = value
  }

  function updateParams(newParams) {
    params.value = { ...params.value, ...newParams }
  }

  function onOverallLengthChange() {
    const availableSpace = params.value.overall_length - params.value.wheel_base
    const currentFO = params.value.front_overhang
    const currentRO = params.value.rear_overhang
    const totalOverhang = currentFO + currentRO
    
    if (totalOverhang > 0) {
      const foRatio = currentFO / totalOverhang
      const roRatio = currentRO / totalOverhang
      params.value.front_overhang = Math.round(availableSpace * foRatio)
      params.value.rear_overhang = Math.round(availableSpace * roRatio)
    } else {
      params.value.front_overhang = Math.round(availableSpace * 0.45)
      params.value.rear_overhang = Math.round(availableSpace * 0.55)
    }
  }

  function onWheelBaseChange() {
    const availableSpace = params.value.overall_length - params.value.wheel_base
    const currentFO = params.value.front_overhang
    const currentRO = params.value.rear_overhang
    const totalOverhang = currentFO + currentRO
    
    if (totalOverhang > 0 && availableSpace > 600) {
      const foRatio = currentFO / totalOverhang
      const roRatio = currentRO / totalOverhang
      params.value.front_overhang = Math.max(300, Math.round(availableSpace * foRatio))
      params.value.rear_overhang = Math.max(300, Math.round(availableSpace * roRatio))
    }
  }

  function onOverhangChange() {
    const newTotal = params.value.front_overhang + params.value.wheel_base + params.value.rear_overhang
    params.value.overall_length = newTotal
  }

  function resetParams() {
    params.value = { ...defaultCarParams, ...currentCarTypeParams.value }
  }

  function toggleViewMode() {
    viewMode.value = viewMode.value === '3d' ? '2d' : '3d'
  }

  function setViewMode(mode) {
    viewMode.value = mode
  }

  function importFromProject(project) {
    if (!project) {
      carType.value = 'sedan'
      brand.value = 'rolls-royce'
      selectedModel.value = null
      selectedColor.value = '#4ade80'
      params.value = { ...defaultCarParams, ...carTypeParams.sedan }
      viewMode.value = '3d'
      generating.value = false
      return
    }
    
    if (project.designData || project.design_data) {
      const data = project.designData || snakeToCamel(project.design_data)
      const newCarType = data.carType || data.car_type || 'sedan'
      const typeParams = carTypeParams[newCarType] || {}
      
      carType.value = newCarType
      brand.value = data.brand || 'rolls-royce'
      selectedModel.value = data.selectedModel || data.selected_model || null
      selectedColor.value = data.selectedColor || data.selected_color || '#4ade80'
      params.value = { ...defaultCarParams, ...typeParams, ...(data.params || {}) }
    } else {
      carType.value = 'sedan'
      brand.value = 'rolls-royce'
      selectedModel.value = null
      selectedColor.value = '#4ade80'
      params.value = { ...defaultCarParams, ...carTypeParams.sedan }
    }
  }

  function exportToProject() {
    return {
      carType: carType.value,
      brand: brand.value,
      selectedModel: selectedModel.value,
      selectedColor: selectedColor.value,
      params: { ...params.value },
      exportTime: new Date().toISOString()
    }
  }

  function clear() {
    carType.value = 'sedan'
    brand.value = 'rolls-royce'
    selectedModel.value = null
    selectedColor.value = '#4ade80'
    params.value = { ...defaultCarParams, ...carTypeParams.sedan }
    viewMode.value = '3d'
    generating.value = false
  }

  return {
    carType,
    brand,
    selectedModel,
    selectedColor,
    params,
    viewMode,
    isLoading,
    generating,
    currentCarTypeParams,
    mergedParams,
    setCarType,
    setBrand,
    selectModel,
    selectColor,
    setGenerating,
    updateParam,
    updateParams,
    onOverallLengthChange,
    onWheelBaseChange,
    onOverhangChange,
    resetParams,
    toggleViewMode,
    setViewMode,
    importFromProject,
    exportToProject,
    clear
  }
})