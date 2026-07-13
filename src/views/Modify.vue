<template>
  <div class="modify-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('modify.title') }}</h2>
        <p>{{ $t('modify.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-button @click="undoChange">{{ $t('modify.undo') }}</el-button>
        <el-button @click="exportState">{{ $t('modify.exportState') }}</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="modify-tabs">
      <el-tab-pane :label="$t('modify.surfaceModify')" name="surface">
        <div class="tab-content">
          <div class="toolbar">
            <el-button type="primary" @click="createSurface">{{ $t('modify.createSurface') }}</el-button>
            <el-button @click="loadSurfaces">{{ $t('modify.refresh') }}</el-button>
          </div>

          <div class="surface-list">
            <el-card v-for="surface in surfaces" :key="surface.surface_id" class="surface-card">
              <template #header>
                <span>{{ surface.surface_id }}</span>
                <el-button type="danger" link @click="deleteSurface(surface.surface_id)">{{ $t('modify.delete') }}</el-button>
              </template>
              <div class="surface-info">
                <div>{{ $t('modify.degree') }}: {{ surface.surface_data.degree_u }} x {{ surface.surface_data.degree_v }}</div>
                <div>{{ $t('modify.controlPoints') }}: {{ surface.surface_data.control_points.length }} x {{ surface.surface_data.control_points[0]?.length || 0 }}</div>
              </div>
              <div class="surface-actions">
                <el-button type="primary" size="small" @click="showModifyDialog(surface, 'surface')">{{ $t('modify.modify') }}</el-button>
                <el-button type="success" size="small" @click="showEvaluateDialog(surface)">{{ $t('modify.evaluate') }}</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="$t('modify.sketchEdit')" name="sketch">
        <div class="tab-content">
          <div class="toolbar">
            <el-button type="primary" @click="createSketch">{{ $t('modify.createSketch') }}</el-button>
            <el-button type="success" @click="showAddEntityDialog = true">{{ $t('modify.addEntity') }}</el-button>
            <el-button type="warning" @click="showAddConstraintDialog = true">{{ $t('modify.addConstraint') }}</el-button>
          </div>

          <div class="sketch-list">
            <el-card v-for="sketch in sketches" :key="sketch.sketch_id" class="sketch-card">
              <template #header>
                <span>{{ sketch.sketch_data.name }}</span>
                <el-tag size="small">{{ sketch.sketch_data.entities.length }} {{ $t('modify.entities') }}</el-tag>
              </template>
              <div class="entities-preview">
                <div v-for="entity in sketch.sketch_data.entities" :key="entity.id" class="entity-item">
                  <el-tag :type="getEntityTypeColor(entity.entity_type)" size="small">
                    {{ $t('modify.' + entity.entity_type) }}
                  </el-tag>
                  <span v-if="entity.entity_type === 'line'">
                    ({{ entity.data.start.x.toFixed(1) }}, {{ entity.data.start.y.toFixed(1) }}) -
                    ({{ entity.data.end.x.toFixed(1) }}, {{ entity.data.end.y.toFixed(1) }})
                  </span>
                  <span v-else-if="entity.entity_type === 'circle'">
                    {{ $t('modify.center') }}: ({{ entity.data.center.x.toFixed(1) }}, {{ entity.data.center.y.toFixed(1) }})
                    {{ $t('modify.radius') }}: {{ entity.data.radius.toFixed(1) }}
                  </span>
                  <span v-else-if="entity.entity_type === 'arc'">
                    {{ $t('modify.radius') }}: {{ entity.data.radius.toFixed(1) }}
                    {{ entity.data.start_angle.toFixed(0) }}° - {{ entity.data.end_angle.toFixed(0) }}°
                  </span>
                </div>
              </div>
              <div class="constraints-list" v-if="sketch.sketch_data.constraints.length > 0">
                <div class="constraints-title">{{ $t('modify.constraints') }}:</div>
                <el-tag v-for="c in sketch.sketch_data.constraints" :key="c.id" size="small" class="constraint-tag">
                  {{ c.type }}
                </el-tag>
              </div>
              <div class="sketch-actions">
                <el-button type="primary" size="small" @click="modifySketch(sketch)">{{ $t('modify.modify') }}</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="$t('modify.automotiveParams')" name="automotive">
        <div class="tab-content">
          <div class="toolbar">
            <el-button @click="loadAutomotiveParameters">{{ $t('modify.refreshParams') }}</el-button>
          </div>

          <el-collapse v-model="activeCategory">
            <el-collapse-item :title="$t('modify.bodyDimensions')" name="body">
              <div class="param-grid">
                <div v-for="param in getParamsByCategory('body')" :key="param.name" class="param-item">
                  <div class="param-label">{{ param.name }}</div>
                  <el-input-number
                    v-model="param.value"
                    :min="param.min_value"
                    :max="param.max_value"
                    :step="param.type === 'angle' ? 1 : 10"
                    @change="applyAutomotiveParam(param.name, param.value)"
                  />
                  <span class="param-unit">{{ param.unit }}</span>
                </div>
              </div>
            </el-collapse-item>
            <el-collapse-item :title="$t('modify.chassisParams')" name="chassis">
              <div class="param-grid">
                <div v-for="param in getParamsByCategory('chassis')" :key="param.name" class="param-item">
                  <div class="param-label">{{ param.name }}</div>
                  <el-input-number
                    v-model="param.value"
                    :min="param.min_value"
                    :max="param.max_value"
                    :step="param.type === 'angle' ? 1 : 10"
                    @change="applyAutomotiveParam(param.name, param.value)"
                  />
                  <span class="param-unit">{{ param.unit }}</span>
                </div>
              </div>
            </el-collapse-item>
            <el-collapse-item :title="$t('modify.exteriorStyling')" name="exterior">
              <div class="param-grid">
                <div v-for="param in getParamsByCategory('exterior')" :key="param.name" class="param-item">
                  <div class="param-label">{{ param.name }}</div>
                  <el-input-number
                    v-model="param.value"
                    :min="param.min_value"
                    :max="param.max_value"
                    :step="param.type === 'angle' ? 1 : 10"
                    @change="applyAutomotiveParam(param.name, param.value)"
                  />
                  <span class="param-unit">{{ param.unit }}</span>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="$t('modify.measurementTools')" name="measurement">
        <div class="tab-content">
          <div class="measurement-tools">
            <el-card class="tool-card">
              <template #header>{{ $t('modify.distanceMeasure') }}</template>
              <el-form :model="distanceForm" label-width="80px">
                <el-form-item :label="$t('modify.startPoint')">
                  <el-input v-model.number="distanceForm.point1.x" placeholder="X" />
                  <el-input v-model.number="distanceForm.point1.y" placeholder="Y" />
                  <el-input v-model.number="distanceForm.point1.z" placeholder="Z" />
                </el-form-item>
                <el-form-item :label="$t('modify.endPoint')">
                  <el-input v-model.number="distanceForm.point2.x" placeholder="X" />
                  <el-input v-model.number="distanceForm.point2.y" placeholder="Y" />
                  <el-input v-model.number="distanceForm.point2.z" placeholder="Z" />
                </el-form-item>
                <el-form-item :label="$t('modify.label')">
                  <el-input v-model="distanceForm.label" :placeholder="$t('modify.label')" />
                </el-form-item>
                <el-button type="primary" @click="measureDistance">{{ $t('modify.measure') }}</el-button>
              </el-form>
              <div v-if="distanceResult" class="measurement-result">
                <div class="result-value">{{ distanceResult.value.toFixed(3) }} {{ distanceResult.unit }}</div>
              </div>
            </el-card>

            <el-card class="tool-card">
              <template #header>{{ $t('modify.angleMeasure') }}</template>
              <el-form :model="angleForm" label-width="80px">
                <el-form-item :label="$t('modify.vertex')">
                  <el-input v-model.number="angleForm.vertex.x" placeholder="X" />
                  <el-input v-model.number="angleForm.vertex.y" placeholder="Y" />
                  <el-input v-model.number="angleForm.vertex.z" placeholder="Z" />
                </el-form-item>
                <el-form-item :label="$t('modify.point1')">
                  <el-input v-model.number="angleForm.point1.x" placeholder="X" />
                  <el-input v-model.number="angleForm.point1.y" placeholder="Y" />
                  <el-input v-model.number="angleForm.point1.z" placeholder="Z" />
                </el-form-item>
                <el-form-item :label="$t('modify.point2')">
                  <el-input v-model.number="angleForm.point2.x" placeholder="X" />
                  <el-input v-model.number="angleForm.point2.y" placeholder="Y" />
                  <el-input v-model.number="angleForm.point2.z" placeholder="Z" />
                </el-form-item>
                <el-button type="primary" @click="measureAngle">{{ $t('modify.measure') }}</el-button>
              </el-form>
              <div v-if="angleResult" class="measurement-result">
                <div class="result-value">{{ angleResult.value.toFixed(3) }} {{ angleResult.unit }}</div>
              </div>
            </el-card>

            <el-card class="tool-card">
              <template #header>{{ $t('modify.curvatureMeasure') }}</template>
              <el-form :model="curvatureForm" label-width="80px">
                <el-form-item :label="$t('modify.surface')">
                  <el-select v-model="curvatureForm.surface_id" :placeholder="$t('modify.surface')">
                    <el-option v-for="s in surfaces" :key="s.surface_id" :label="s.surface_id" :value="s.surface_id" />
                  </el-select>
                </el-form-item>
                <el-form-item :label="$t('modify.uParam')">
                  <el-slider v-model="curvatureForm.u" :min="0" :max="1" :step="0.01" show-input />
                </el-form-item>
                <el-form-item :label="$t('modify.vParam')">
                  <el-slider v-model="curvatureForm.v" :min="0" :max="1" :step="0.01" show-input />
                </el-form-item>
                <el-button type="primary" @click="measureCurvature">{{ $t('modify.measure') }}</el-button>
              </el-form>
              <div v-if="curvatureResult" class="curvature-result">
                <div class="curv-item">{{ $t('modify.gaussianCurvature') }}: {{ curvatureResult.gaussian_curvature?.toFixed(6) }}</div>
                <div class="curv-item">{{ $t('modify.meanCurvature') }}: {{ curvatureResult.mean_curvature?.toFixed(6) }}</div>
                <div class="curv-item">{{ $t('modify.curvatureRadius1') }}: {{ curvatureResult.curvature_radius_1?.toFixed(2) }}</div>
                <div class="curv-item">{{ $t('modify.curvatureRadius2') }}: {{ curvatureResult.curvature_radius_2?.toFixed(2) }}</div>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showCreateSurfaceDialog" :title="$t('modify.createNurbsSurface')" width="600px">
      <el-form :model="surfaceForm" label-width="100px">
        <el-form-item :label="$t('modify.degreeU')">
          <el-input-number v-model="surfaceForm.degree_u" :min="1" :max="10" />
        </el-form-item>
        <el-form-item :label="$t('modify.degreeV')">
          <el-input-number v-model="surfaceForm.degree_v" :min="1" :max="10" />
        </el-form-item>
        <el-form-item :label="$t('modify.numControlU')">
          <el-input-number v-model="surfaceForm.num_u" :min="surfaceForm.degree_u + 1" :max="20" />
        </el-form-item>
        <el-form-item :label="$t('modify.numControlV')">
          <el-input-number v-model="surfaceForm.num_v" :min="surfaceForm.degree_v + 1" :max="20" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateSurfaceDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitCreateSurface">{{ $t('common.create') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showModifyDialogFlag" :title="$t('modify.modify')" width="500px">
      <el-form :model="modifyForm" label-width="100px">
        <el-form-item :label="$t('modify.operationType')">
          <el-select v-model="modifyForm.operation_type">
            <el-option :label="$t('modify.translate')" value="translate" />
            <el-option :label="$t('modify.scale')" value="scale" />
            <el-option :label="$t('modify.rotate')" value="rotate" />
            <el-option :label="$t('modify.offset')" value="offset" />
          </el-select>
        </el-form-item>
        <template v-if="modifyForm.operation_type === 'translate'">
          <el-form-item :label="$t('modify.xOffset')">
            <el-input-number v-model="modifyForm.dx" :step="1" />
          </el-form-item>
          <el-form-item :label="$t('modify.yOffset')">
            <el-input-number v-model="modifyForm.dy" :step="1" />
          </el-form-item>
          <el-form-item :label="$t('modify.zOffset')">
            <el-input-number v-model="modifyForm.dz" :step="1" />
          </el-form-item>
        </template>
        <template v-else-if="modifyForm.operation_type === 'scale'">
          <el-form-item :label="$t('modify.xScale')">
            <el-input-number v-model="modifyForm.sx" :min="0.1" :max="10" :step="0.1" />
          </el-form-item>
          <el-form-item :label="$t('modify.yScale')">
            <el-input-number v-model="modifyForm.sy" :min="0.1" :max="10" :step="0.1" />
          </el-form-item>
          <el-form-item :label="$t('modify.zScale')">
            <el-input-number v-model="modifyForm.sz" :min="0.1" :max="10" :step="0.1" />
          </el-form-item>
        </template>
        <template v-else-if="modifyForm.operation_type === 'rotate'">
          <el-form-item :label="$t('modify.angle')">
            <el-input-number v-model="modifyForm.angle" :min="-360" :max="360" />
          </el-form-item>
          <el-form-item :label="$t('modify.axis')">
            <el-select v-model="modifyForm.axis">
              <el-option :label="$t('modify.xAxis')" value="x" />
              <el-option :label="$t('modify.yAxis')" value="y" />
              <el-option :label="$t('modify.zAxis')" value="z" />
            </el-select>
          </el-form-item>
        </template>
        <template v-else-if="modifyForm.operation_type === 'offset'">
          <el-form-item :label="$t('modify.offsetDistance')">
            <el-input-number v-model="modifyForm.distance" :step="0.1" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showModifyDialogFlag = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitModify">{{ $t('modify.apply') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEvaluateDialogFlag" :title="$t('modify.surfaceEvaluation')" width="500px">
      <el-form :model="evaluateForm" label-width="80px">
        <el-form-item :label="$t('modify.uParam')">
          <el-slider v-model="evaluateForm.u" :min="0" :max="1" :step="0.01" show-input />
        </el-form-item>
        <el-form-item :label="$t('modify.vParam')">
          <el-slider v-model="evaluateForm.v" :min="0" :max="1" :step="0.01" show-input />
        </el-form-item>
        <el-button type="primary" @click="evaluatePoint">{{ $t('modify.evaluatePoint') }}</el-button>
      </el-form>
      <div v-if="evaluateResult" class="evaluate-result">
        <div class="result-section">
          <h4>{{ $t('modify.pointCoord') }}</h4>
          <div>X: {{ evaluateResult.point?.[0]?.toFixed(4) }}</div>
          <div>Y: {{ evaluateResult.point?.[1]?.toFixed(4) }}</div>
          <div>Z: {{ evaluateResult.point?.[2]?.toFixed(4) }}</div>
        </div>
        <div class="result-section">
          <h4>{{ $t('modify.normalVector') }}</h4>
          <div>X: {{ evaluateResult.normal?.[0]?.toFixed(4) }}</div>
          <div>Y: {{ evaluateResult.normal?.[1]?.toFixed(4) }}</div>
          <div>Z: {{ evaluateResult.normal?.[2]?.toFixed(4) }}</div>
        </div>
        <div class="result-section">
          <h4>{{ $t('modify.curvature') }}</h4>
          <div>{{ $t('modify.gaussian') }}: {{ evaluateResult.curvature?.gaussian_curvature?.toFixed(6) }}</div>
          <div>{{ $t('modify.mean') }}: {{ evaluateResult.curvature?.mean_curvature?.toFixed(6) }}</div>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showAddEntityDialog" :title="$t('modify.addSketchEntity')" width="500px">
      <el-form :model="entityForm" label-width="80px">
        <el-form-item :label="$t('modify.entityType')">
          <el-select v-model="entityForm.entity_type">
            <el-option :label="$t('modify.line')" value="line" />
            <el-option :label="$t('modify.circle')" value="circle" />
            <el-option :label="$t('modify.arc')" value="arc" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('modify.sketch')">
          <el-select v-model="entityForm.sketch_id" :placeholder="$t('modify.sketch')">
            <el-option v-for="s in sketches" :key="s.sketch_id" :label="s.sketch_data.name" :value="s.sketch_id" />
          </el-select>
        </el-form-item>
        <template v-if="entityForm.entity_type === 'line'">
          <el-form-item :label="$t('modify.startPoint')">
            <el-input v-model.number="entityForm.start_x" placeholder="X" />
            <el-input v-model.number="entityForm.start_y" placeholder="Y" />
          </el-form-item>
          <el-form-item :label="$t('modify.endPoint')">
            <el-input v-model.number="entityForm.end_x" placeholder="X" />
            <el-input v-model.number="entityForm.end_y" placeholder="Y" />
          </el-form-item>
        </template>
        <template v-else-if="entityForm.entity_type === 'circle'">
          <el-form-item :label="$t('modify.center')">
            <el-input v-model.number="entityForm.center_x" placeholder="X" />
            <el-input v-model.number="entityForm.center_y" placeholder="Y" />
          </el-form-item>
          <el-form-item :label="$t('modify.radius')">
            <el-input-number v-model="entityForm.radius" :min="0.1" />
          </el-form-item>
        </template>
        <template v-else-if="entityForm.entity_type === 'arc'">
          <el-form-item :label="$t('modify.center')">
            <el-input v-model.number="entityForm.center_x" placeholder="X" />
            <el-input v-model.number="entityForm.center_y" placeholder="Y" />
          </el-form-item>
          <el-form-item :label="$t('modify.radius')">
            <el-input-number v-model="entityForm.radius" :min="0.1" />
          </el-form-item>
          <el-form-item :label="$t('modify.startAngle')">
            <el-input-number v-model="entityForm.start_angle" :min="0" :max="360" />
          </el-form-item>
          <el-form-item :label="$t('modify.endAngle')">
            <el-input-number v-model="entityForm.end_angle" :min="0" :max="360" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showAddEntityDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="addEntity">{{ $t('common.create') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showAddConstraintDialog" :title="$t('modify.addConstraint')" width="500px">
      <el-form :model="constraintForm" label-width="80px">
        <el-form-item :label="$t('modify.constraintType')">
          <el-select v-model="constraintForm.constraint_type">
            <el-option label="Coincident" value="coincident" />
            <el-option label="Horizontal" value="horizontal" />
            <el-option label="Vertical" value="vertical" />
            <el-option label="Parallel" value="parallel" />
            <el-option label="Perpendicular" value="perpendicular" />
            <el-option label="Tangent" value="tangent" />
            <el-option label="Equal Length" value="equal_length" />
            <el-option label="Equal Radius" value="equal_radius" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('modify.sketch')">
          <el-select v-model="constraintForm.sketch_id" :placeholder="$t('modify.sketch')">
            <el-option v-for="s in sketches" :key="s.sketch_id" :label="s.sketch_data.name" :value="s.sketch_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Entity IDs">
          <el-select v-model="constraintForm.entity_ids" multiple placeholder="Select entities">
            <el-option v-for="e in getSketchEntities()" :key="e.id" :label="`${e.entity_type} #${e.id}`" :value="e.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddConstraintDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="addConstraint">{{ $t('common.create') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { modifyAPI } from '../services/api'

const { t } = useI18n()

const activeTab = ref('surface')
const activeCategory = ref('body')

const surfaces = ref([])
const sketches = ref([])
const automotiveParams = ref([])

const showCreateSurfaceDialog = ref(false)
const showModifyDialogFlag = ref(false)
const showEvaluateDialogFlag = ref(false)
const showAddEntityDialog = ref(false)
const showAddConstraintDialog = ref(false)

const currentEntity = ref(null)
const currentSurface = ref(null)

const surfaceForm = reactive({
  degree_u: 3,
  degree_v: 3,
  num_u: 5,
  num_v: 5
})

const modifyForm = reactive({
  operation_type: 'translate',
  dx: 0, dy: 0, dz: 0,
  sx: 1, sy: 1, sz: 1,
  angle: 0, axis: 'z',
  distance: 0
})

const evaluateForm = reactive({ u: 0.5, v: 0.5 })
const evaluateResult = ref(null)

const distanceForm = reactive({
  point1: { x: 0, y: 0, z: 0 },
  point2: { x: 100, y: 0, z: 0 },
  label: ''
})
const distanceResult = ref(null)

const angleForm = reactive({
  vertex: { x: 0, y: 0, z: 0 },
  point1: { x: 100, y: 0, z: 0 },
  point2: { x: 0, y: 100, z: 0 }
})
const angleResult = ref(null)

const curvatureForm = reactive({
  surface_id: '',
  u: 0.5,
  v: 0.5
})
const curvatureResult = ref(null)

const entityForm = reactive({
  sketch_id: '',
  entity_type: 'line',
  start_x: 0, start_y: 0,
  end_x: 100, end_y: 0,
  center_x: 0, center_y: 0,
  radius: 50,
  start_angle: 0,
  end_angle: 180
})

const constraintForm = reactive({
  sketch_id: '',
  constraint_type: 'horizontal',
  entity_ids: []
})

const createSurface = () => {
  showCreateSurfaceDialog.value = true
}

const submitCreateSurface = async () => {
  const controlPoints = []
  for (let i = 0; i < surfaceForm.num_u; i++) {
    const row = []
    for (let j = 0; j < surfaceForm.num_v; j++) {
      row.push({
        x: i * 10,
        y: j * 10,
        z: Math.sin(i / 2) * Math.cos(j / 2) * 5,
        weight: 1.0
      })
    }
    controlPoints.push(row)
  }

  try {
    const response = await modifyAPI.createSurface({
      degree_u: surfaceForm.degree_u,
      degree_v: surfaceForm.degree_v,
      control_points: controlPoints
    })
    surfaces.value.push(response.data)
    showCreateSurfaceDialog.value = false
    ElMessage.success(t('modify.createSurfaceSuccess'))
  } catch (error) {
    ElMessage.error(t('modify.createSurfaceFailed'))
  }
}

const loadSurfaces = async () => {
  if (surfaces.value.length === 0) {
    ElMessage.info(t('modify.noSurfaces'))
  }
}

const deleteSurface = async (surfaceId) => {
  try {
    await modifyAPI.deleteSurface(surfaceId)
    surfaces.value = surfaces.value.filter(s => s.surface_id !== surfaceId)
    ElMessage.success(t('modify.deleteSurfaceSuccess'))
  } catch (error) {
    ElMessage.error(t('modify.deleteSurfaceFailed'))
  }
}

const showModifyDialog = (surface, type) => {
  currentSurface.value = surface
  currentEntity.value = type
  showModifyDialogFlag.value = true
}

const submitModify = async () => {
  if (!currentSurface.value) return

  const parameters = {}
  if (modifyForm.operation_type === 'translate') {
    parameters.dx = modifyForm.dx
    parameters.dy = modifyForm.dy
    parameters.dz = modifyForm.dz
  } else if (modifyForm.operation_type === 'scale') {
    parameters.sx = modifyForm.sx
    parameters.sy = modifyForm.sy
    parameters.sz = modifyForm.sz
  } else if (modifyForm.operation_type === 'rotate') {
    parameters.angle = modifyForm.angle
    parameters.axis = modifyForm.axis
  } else if (modifyForm.operation_type === 'offset') {
    parameters.distance = modifyForm.distance
  }

  try {
    await modifyAPI.modifySurface(currentSurface.value.surface_id, {
      surface_id: currentSurface.value.surface_id,
      operation_type: modifyForm.operation_type,
      parameters
    })
    showModifyDialogFlag.value = false
    ElMessage.success(t('modify.modifyApplied'))
    loadSurfaces()
  } catch (error) {
    ElMessage.error(t('modify.modifyFailed'))
  }
}

const showEvaluateDialog = (surface) => {
  currentSurface.value = surface
  curvatureForm.surface_id = surface.surface_id
  showEvaluateDialogFlag.value = true
}

const evaluatePoint = async () => {
  if (!currentSurface.value) return

  try {
    const response = await modifyAPI.evaluateSurface(
      currentSurface.value.surface_id,
      evaluateForm.u,
      evaluateForm.v
    )
    evaluateResult.value = response.data
  } catch (error) {
    ElMessage.error(t('modify.evaluateFailed'))
  }
}

const createSketch = async () => {
  try {
    const response = await modifyAPI.createSketch({ name: t('modify.newSketch') })
    sketches.value.push(response.data)
    ElMessage.success(t('modify.createSketchSuccess'))
  } catch (error) {
    ElMessage.error(t('modify.createSketchFailed'))
  }
}

const loadSketches = async () => {
  if (sketches.value.length === 0) {
    ElMessage.info(t('modify.noSketches'))
  }
}

const getEntityTypeColor = (type) => {
  const colors = { line: '', circle: 'success', arc: 'warning', point: 'info' }
  return colors[type] || ''
}

const getSketchEntities = () => {
  if (!constraintForm.sketch_id) return []
  const sketch = sketches.value.find(s => s.sketch_id === constraintForm.sketch_id)
  return sketch ? sketch.sketch_data.entities : []
}

const addEntity = async () => {
  if (!entityForm.sketch_id) {
    ElMessage.warning(t('modify.selectSketch'))
    return
  }

  let data = {}
  if (entityForm.entity_type === 'line') {
    data = {
      start: { x: entityForm.start_x, y: entityForm.start_y },
      end: { x: entityForm.end_x, y: entityForm.end_y }
    }
  } else if (entityForm.entity_type === 'circle') {
    data = {
      center: { x: entityForm.center_x, y: entityForm.center_y },
      radius: entityForm.radius
    }
  } else if (entityForm.entity_type === 'arc') {
    data = {
      center: { x: entityForm.center_x, y: entityForm.center_y },
      radius: entityForm.radius,
      start_angle: entityForm.start_angle,
      end_angle: entityForm.end_angle
    }
  }

  try {
    await modifyAPI.addSketchEntity(entityForm.sketch_id, {
      entity_type: entityForm.entity_type,
      data
    })
    showAddEntityDialog.value = false
    ElMessage.success(t('modify.addEntitySuccess'))
    loadSketches()
  } catch (error) {
    ElMessage.error(t('modify.addEntityFailed'))
  }
}

const addConstraint = async () => {
  if (!constraintForm.sketch_id || constraintForm.entity_ids.length === 0) {
    ElMessage.warning(t('modify.selectSketchAndEntities'))
    return
  }

  try {
    await modifyAPI.addSketchConstraint(constraintForm.sketch_id, {
      constraint_type: constraintForm.constraint_type,
      entity_ids: constraintForm.entity_ids
    })
    showAddConstraintDialog.value = false
    ElMessage.success(t('modify.addConstraintSuccess'))
    loadSketches()
  } catch (error) {
    ElMessage.error(t('modify.addConstraintFailed'))
  }
}

const modifySketch = (sketch) => {
  entityForm.sketch_id = sketch.sketch_id
  showModifyDialogFlag.value = true
}

const loadAutomotiveParameters = async () => {
  try {
    const response = await modifyAPI.getAutomotiveParameters()
    automotiveParams.value = Object.entries(response.data.parameters).map(([key, value]) => ({
      key,
      ...value
    }))
  } catch (error) {
    ElMessage.error(t('modify.loadParamsFailed'))
  }
}

const getParamsByCategory = (category) => {
  return automotiveParams.value.filter(p => p.category === category)
}

const applyAutomotiveParam = async (name, value) => {
  try {
    await modifyAPI.applyAutomotiveParameter(name, value)
  } catch (error) {
    console.error('参数应用失败:', error)
  }
}

const measureDistance = async () => {
  try {
    const response = await modifyAPI.measureDistance({
      point1: distanceForm.point1,
      point2: distanceForm.point2,
      label: distanceForm.label
    })
    distanceResult.value = response.data.measurement
  } catch (error) {
    ElMessage.error(t('modify.distanceMeasureFailed'))
  }
}

const measureAngle = async () => {
  try {
    const response = await modifyAPI.measureAngle({
      vertex: angleForm.vertex,
      point1: angleForm.point1,
      point2: angleForm.point2
    })
    angleResult.value = response.data.measurement
  } catch (error) {
    ElMessage.error(t('modify.angleMeasureFailed'))
  }
}

const measureCurvature = async () => {
  if (!curvatureForm.surface_id) {
    ElMessage.warning(t('modify.selectSurface'))
    return
  }

  try {
    const response = await modifyAPI.measureCurvature({
      surface_id: curvatureForm.surface_id,
      u: curvatureForm.u,
      v: curvatureForm.v
    })
    curvatureResult.value = response.data.curvature
  } catch (error) {
    ElMessage.error(t('modify.measureCurvatureFailed'))
  }
}

const undoChange = async () => {
  try {
    await modifyAPI.undo()
    ElMessage.success(t('modify.undoSuccess'))
    loadSurfaces()
  } catch (error) {
    ElMessage.error(t('modify.undoFailed'))
  }
}

const exportState = async () => {
  try {
    const response = await modifyAPI.exportState()
    console.log('状态导出:', response.data)
    ElMessage.success(t('modify.exportStateSuccess'))
  } catch (error) {
    ElMessage.error(t('modify.exportStateFailed'))
  }
}

onMounted(() => {
  loadSurfaces()
  loadSketches()
  loadAutomotiveParameters()
})
</script>

<style>
.modify-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.modify-tabs { background: white; padding: 20px; border-radius: 8px; }

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.surface-list, .sketch-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
}

.surface-card, .sketch-card {
  margin-bottom: 10px;
}

.surface-info { margin: 10px 0; font-size: 14px; color: #666; }

.entities-preview {
  margin: 10px 0;
}

.entity-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 5px;
  font-size: 13px;
}

.constraints-list { margin-top: 10px; }
.constraints-title { font-size: 12px; color: #666; margin-bottom: 5px; }
.constraint-tag { margin-right: 5px; }

.param-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 15px;
}

.param-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.param-label { min-width: 100px; }
.param-unit { color: #999; margin-left: 5px; }

.measurement-tools {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
}

.tool-card { height: fit-content; }

.measurement-result {
  margin-top: 15px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
  text-align: center;
}

.result-value { font-size: 24px; font-weight: bold; color: #007bff; }

.curvature-result {
  margin-top: 15px;
}

.curv-item { margin: 5px 0; font-size: 14px; }

.evaluate-result {
  margin-top: 15px;
}

.result-section {
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.result-section h4 { margin: 0 0 10px 0; font-size: 14px; color: #666; }
</style>