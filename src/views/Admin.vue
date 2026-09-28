<template>
  <div class="admin-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">{{ t('admin.title') }}</h2>
        <p class="page-subtitle">{{ t('admin.subtitle') }}</p>
      </div>
      <el-tag v-if="auth.isSuperadmin" type="danger" effect="dark" size="large">
        {{ t('admin.roleSuperadmin') }}
      </el-tag>
      <el-tag v-else type="warning" effect="dark" size="large">
        {{ t('admin.roleAdmin') }}
      </el-tag>
    </div>

    <el-tabs v-model="activeTab" class="admin-tabs">
      <!-- ── 登录记录（admin+） ─────────────── -->
      <el-tab-pane :label="t('admin.tabLoginRecords')" name="records">
        <div class="toolbar">
          <el-input
            v-model="recordEmailFilter"
            :placeholder="t('admin.filterEmail')"
            clearable
            class="filter-input"
            @keyup.enter="loadLoginRecords"
          />
          <el-button type="primary" plain @click="loadLoginRecords">
            <el-icon><Search /></el-icon>{{ t('admin.search') }}
          </el-button>
          <el-button @click="loadLoginRecords">
            <el-icon><Refresh /></el-icon>{{ t('admin.refresh') }}
          </el-button>
        </div>

        <el-table :data="loginRecords" v-loading="recordsLoading" stripe class="admin-table">
          <el-table-column prop="created_at" :label="t('admin.colTime')" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="email" :label="t('admin.colEmail')" min-width="200" />
          <el-table-column :label="t('admin.colResult')" width="100">
            <template #default="{ row }">
              <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                {{ row.success ? t('admin.resultSuccess') : t('admin.resultFail') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reason" :label="t('admin.colReason')" width="140" />
          <el-table-column prop="method" :label="t('admin.colMethod')" width="100" />
          <el-table-column prop="ip" :label="t('admin.colIp')" width="140" />
        </el-table>
      </el-tab-pane>

      <!-- ── 用户管理（admin 可见；superadmin 可操作） ── -->
      <el-tab-pane :label="t('admin.tabUsers')" name="users">
        <div class="toolbar">
          <el-button @click="loadUsers">
            <el-icon><Refresh /></el-icon>{{ t('admin.refresh') }}
          </el-button>
          <el-alert
            v-if="!auth.isSuperadmin"
            :title="t('admin.readOnlyHint')"
            type="info"
            :closable="false"
            class="readonly-alert"
          />
        </div>

        <el-table :data="users" v-loading="usersLoading" stripe class="admin-table">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="email" :label="t('admin.colEmail')" min-width="200" />
          <el-table-column prop="username" :label="t('admin.colUsername')" min-width="140" />
          <el-table-column :label="t('admin.colRole')" width="180">
            <template #default="{ row }">
              <el-select
                v-if="auth.isSuperadmin"
                :model-value="row.role"
                size="small"
                @change="(val) => changeRole(row, val)"
              >
                <el-option :label="t('admin.roleUser')" value="user" />
                <el-option :label="t('admin.roleAdmin')" value="admin" />
                <el-option :label="t('admin.roleSuperadmin')" value="superadmin" />
              </el-select>
              <el-tag v-else :type="roleTagType(row.role)" size="small">
                {{ roleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('admin.colStatus')" width="110">
            <template #default="{ row }">
              <el-switch
                v-if="auth.isSuperadmin"
                :model-value="row.is_active"
                :disabled="row.id === auth.user?.id"
                @change="(val) => toggleActive(row, val)"
              />
              <el-tag v-else :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? t('admin.statusActive') : t('admin.statusDisabled') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('admin.colActions')" width="140">
            <template #default="{ row }">
              <el-button
                v-if="auth.isSuperadmin"
                size="small"
                link
                type="warning"
                @click="openResetDialog(row)"
              >{{ t('admin.resetPassword') }}</el-button>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ── 后端错误（仅 superadmin） ───────── -->
      <el-tab-pane
        :label="t('admin.tabBackendErrors')"
        name="errors"
        :disabled="!auth.isSuperadmin"
      >
        <div class="toolbar">
          <el-button type="primary" plain @click="loadBackendErrors">
            <el-icon><Refresh /></el-icon>{{ t('admin.refresh') }}
          </el-button>
          <span class="log-path">{{ errorFilePath }}</span>
        </div>
        <pre v-loading="errorsLoading" class="error-log-box">{{ errorContent }}</pre>
      </el-tab-pane>

      <!-- ── 审计日志（仅 superadmin） ───────── -->
      <el-tab-pane
        :label="t('admin.tabAuditLogs')"
        name="audit"
        :disabled="!auth.isSuperadmin"
      >
        <div class="toolbar">
          <el-button type="primary" plain @click="loadAuditLogs">
            <el-icon><Refresh /></el-icon>{{ t('admin.refresh') }}
          </el-button>
        </div>
        <el-table :data="auditLogs" v-loading="auditLoading" stripe class="admin-table">
          <el-table-column prop="created_at" :label="t('admin.colTime')" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="admin_id" :label="t('admin.colAdminId')" width="100" />
          <el-table-column prop="action" :label="t('admin.colAction')" width="150" />
          <el-table-column prop="target_id" :label="t('admin.colTargetId')" width="100" />
          <el-table-column prop="detail_json" :label="t('admin.colDetail')" min-width="240" />
          <el-table-column prop="ip" :label="t('admin.colIp')" width="140" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 重置密码对话框 -->
    <el-dialog
      v-model="resetDialogVisible"
      :title="t('admin.resetPasswordTitle')"
      width="400px"
    >
      <p class="reset-target">{{ resetTarget?.email }}</p>
      <el-input
        v-model="newPassword"
        type="password"
        show-password
        :placeholder="t('admin.newPasswordPlaceholder')"
      />
      <template #footer>
        <el-button @click="resetDialogVisible = false">{{ t('admin.cancel') }}</el-button>
        <el-button type="primary" @click="submitResetPassword">{{ t('admin.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { adminAPI } from '../api'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n({ useScope: 'global' })
const auth = useAuthStore()

const activeTab = ref('records')

// ── 登录记录 ─────────────────────────────────
const loginRecords = ref([])
const recordsLoading = ref(false)
const recordEmailFilter = ref('')

const loadLoginRecords = async () => {
  recordsLoading.value = true
  try {
    const params = {}
    if (recordEmailFilter.value.trim()) {
      params.email = recordEmailFilter.value.trim()
    }
    const { data } = await adminAPI.loginRecords(params)
    loginRecords.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('admin.loadFailed'))
  } finally {
    recordsLoading.value = false
  }
}

// ── 用户管理 ─────────────────────────────────
const users = ref([])
const usersLoading = ref(false)

const loadUsers = async () => {
  usersLoading.value = true
  try {
    const { data } = await adminAPI.users()
    users.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('admin.loadFailed'))
  } finally {
    usersLoading.value = false
  }
}

const toggleActive = async (row, val) => {
  try {
    await adminAPI.setActive(row.id, val)
    row.is_active = val
    ElMessage.success(t('admin.updateOk'))
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('admin.updateFailed'))
  }
}

const changeRole = async (row, val) => {
  try {
    await adminAPI.setRole(row.id, val)
    row.role = val
    ElMessage.success(t('admin.updateOk'))
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('admin.updateFailed'))
  }
}

const resetDialogVisible = ref(false)
const resetTarget = ref(null)
const newPassword = ref('')

const openResetDialog = (row) => {
  resetTarget.value = row
  newPassword.value = ''
  resetDialogVisible.value = true
}

const submitResetPassword = async () => {
  if (newPassword.value.length < 6) {
    ElMessage.warning(t('admin.passwordTooShort'))
    return
  }
  try {
    await adminAPI.resetPassword(resetTarget.value.id, newPassword.value)
    resetDialogVisible.value = false
    ElMessage.success(t('admin.updateOk'))
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('admin.updateFailed'))
  }
}

// ── 后端错误日志 ─────────────────────────────
const errorContent = ref('')
const errorFilePath = ref('')
const errorsLoading = ref(false)

const loadBackendErrors = async () => {
  errorsLoading.value = true
  try {
    const { data } = await adminAPI.backendErrors(200)
    errorContent.value = data.content
    errorFilePath.value = data.file_path
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('admin.loadFailed'))
  } finally {
    errorsLoading.value = false
  }
}

// ── 审计日志 ─────────────────────────────────
const auditLogs = ref([])
const auditLoading = ref(false)

const loadAuditLogs = async () => {
  auditLoading.value = true
  try {
    const { data } = await adminAPI.auditLogs(100)
    auditLogs.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('admin.loadFailed'))
  } finally {
    auditLoading.value = false
  }
}

// ── 展示辅助 ─────────────────────────────────
const formatTime = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
         `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const roleLabel = (role) => t(`admin.role${role.charAt(0).toUpperCase()}${role.slice(1)}`)
const roleTagType = (role) =>
  role === 'superadmin' ? 'danger' : role === 'admin' ? 'warning' : 'info'

onMounted(() => {
  loadLoginRecords()
  loadUsers()
  if (auth.isSuperadmin) {
    loadBackendErrors()
    loadAuditLogs()
  }
})
</script>

<style scoped>
.admin-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 6px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-muted, rgba(255,255,255,0.4));
  margin: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.filter-input {
  max-width: 260px;
}

.readonly-alert {
  max-width: 420px;
}

.admin-table {
  border-radius: 8px;
}

.text-muted {
  color: var(--text-muted, rgba(255,255,255,0.4));
}

.error-log-box {
  background: #0c0c12;
  border: 1px solid var(--border-color, rgba(255,255,255,0.08));
  border-radius: 8px;
  padding: 14px;
  font-size: 12px;
  line-height: 1.7;
  color: #e5e7eb;
  max-height: 62vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-path {
  font-size: 11px;
  color: var(--text-muted, rgba(255,255,255,0.4));
}

.reset-target {
  font-size: 13px;
  margin-bottom: 12px;
  color: var(--text-secondary, rgba(255,255,255,0.65));
}
</style>
