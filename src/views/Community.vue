<template>
  <div class="community-page">
    <!-- 页头 -->
    <div class="page-hero">
      <h1 class="hero-title">{{ t('community.title') }}</h1>
      <p class="hero-subtitle">{{ t('community.subtitle') }}</p>
    </div>

    <div class="community-layout">
      <!-- 帖子流 -->
      <div class="posts-column">
        <div v-if="!posts.length && !loading" class="empty-hint">
          <el-empty :description="t('community.noPosts')" :image-size="70" />
        </div>

        <div class="post-card" v-for="p in posts" :key="p.id" v-loading="loading">
          <div class="post-head">
            <div class="avatar">{{ p.guest_name.charAt(0).toUpperCase() }}</div>
            <div class="post-meta">
              <span class="post-name">{{ p.guest_name }}</span>
              <span class="post-time">{{ formatTime(p.created_at) }}</span>
            </div>
            <el-tag v-if="p.is_official" size="small" type="success" effect="dark" round>
              {{ t('community.officialBadge') }}
            </el-tag>
          </div>
          <p class="post-content">{{ p.content }}</p>

          <div class="post-actions">
            <button class="action-btn" :class="{ liked: likedIds.has(p.id) }"
              @click="like(p)">
              <el-icon><Pointer /></el-icon>
              {{ p.likes_count || '' }} {{ t('community.like') }}
            </button>
            <button class="action-btn" @click="toggleReplyBox(p.id)">
              <el-icon><ChatDotRound /></el-icon>
              {{ t('community.reply') }}
            </button>
            <button v-if="auth.isSuperadmin" class="action-btn danger"
              @click="hidePost(p)">
              <el-icon><Hide /></el-icon>{{ t('community.hide') }}
            </button>
          </div>

          <!-- 回复列表 -->
          <div class="reply-list" v-if="p.replies?.length">
            <div class="reply-item" v-for="r in p.replies" :key="r.id">
              <div class="reply-head">
                <span class="reply-name">{{ r.guest_name }}</span>
                <span class="reply-time">{{ formatTime(r.created_at) }}</span>
              </div>
              <p class="reply-content">{{ r.content }}</p>
            </div>
          </div>

          <!-- 回复框 -->
          <div class="reply-box" v-if="replyOpenId === p.id">
            <el-input v-if="!auth.user" v-model="replyName" size="small"
              :placeholder="t('community.yourName')" class="reply-name-input" />
            <div class="reply-input-row">
              <el-input v-model="replyText" size="small"
                :placeholder="t('community.replyPlaceholder')" />
              <el-button size="small" type="primary" @click="doReply(p)">
                {{ t('community.send') }}
              </el-button>
            </div>
          </div>
        </div>

        <div class="pagination" v-if="total > pageSize">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            small
            background
            @current-change="loadPosts" />
        </div>
      </div>

      <!-- 侧栏：发帖 + 引用线索 -->
      <div class="side-column">
        <div class="side-card">
          <h3 class="side-title">{{ t('community.newPost') }}</h3>
          <el-input v-if="!auth.user" v-model="postForm.guest_name" size="small"
            :placeholder="t('community.yourName')" class="form-item" />
          <el-input v-model="postForm.content" type="textarea" :rows="4"
            :placeholder="t('community.postPlaceholder')" class="form-item" />
          <el-button type="primary" class="submit-btn" @click="createPost">
            {{ t('community.publish') }}
          </el-button>
        </div>

        <div class="side-card">
          <h3 class="side-title">{{ t('community.refTitle') }}</h3>
          <p class="side-desc">{{ t('community.refDesc') }}</p>
          <el-input v-model="refForm.source_url" size="small"
            :placeholder="t('community.refUrl')" class="form-item" />
          <el-input v-model="refForm.source_platform" size="small"
            :placeholder="t('community.refPlatform')" class="form-item" />
          <el-button size="small" class="submit-btn" @click="submitRef">
            {{ t('community.submitRef') }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pointer, ChatDotRound, Hide } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { analyticsAPI } from '../api'
import { useAuthStore } from '../stores/auth'
import { tracker } from '../utils/tracker'

const { t } = useI18n({ useScope: 'global' })
const auth = useAuthStore()

const posts = ref([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)

const postForm = reactive({ guest_name: '', content: '' })
const replyOpenId = ref(null)
const replyName = ref('')
const replyText = ref('')
const refForm = reactive({ source_url: '', source_platform: '' })

// 已点赞帖子（localStorage 持久化，防重复点赞）
const likedIds = ref(new Set(
  JSON.parse(localStorage.getItem('evoai_liked_posts') || '[]')))

function persistLiked() {
  localStorage.setItem('evoai_liked_posts',
    JSON.stringify([...likedIds.value]))
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
         `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadPosts(p = 1) {
  loading.value = true
  try {
    const { data } = await analyticsAPI.listMessages(p, pageSize.value)
    posts.value = data.items
    total.value = data.total
  } catch {
    ElMessage.error(t('community.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function createPost() {
  const name = auth.user ? auth.user.username : postForm.guest_name.trim()
  if (!name || !postForm.content.trim()) {
    ElMessage.warning(t('community.formRequired'))
    return
  }
  try {
    await analyticsAPI.createMessage({
      guest_name: name,
      content: postForm.content.trim(),
      visitor_id: tracker.visitorId,
    })
    ElMessage.success(t('community.published'))
    postForm.guest_name = ''
    postForm.content = ''
    page.value = 1  // 数据回到第 1 页，同步分页器高亮
    await loadPosts(1)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('community.sendFailed'))
  }
}

function toggleReplyBox(id) {
  replyOpenId.value = replyOpenId.value === id ? null : id
  replyText.value = ''
}

async function doReply(p) {
  const name = auth.user ? auth.user.username : replyName.value.trim()
  if (!name || !replyText.value.trim()) {
    ElMessage.warning(t('community.formRequired'))
    return
  }
  try {
    await analyticsAPI.replyMessage(p.id, {
      reply: replyText.value.trim(),
      guest_name: name,
      visitor_id: tracker.visitorId,
    })
    ElMessage.success(t('community.published'))
    replyOpenId.value = null
    replyText.value = ''
    await loadPosts(page.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('community.sendFailed'))
  }
}

async function like(p) {
  if (likedIds.value.has(p.id)) return
  try {
    const { data } = await analyticsAPI.likeMessage(p.id)
    p.likes_count = data.likes_count
    likedIds.value.add(p.id)
    persistLiked()
  } catch {}
}

async function hidePost(p) {
  try {
    await analyticsAPI.hideMessage(p.id)
    await loadPosts(page.value)
  } catch {}
}

async function submitRef() {
  if (!refForm.source_url.trim() || !refForm.source_platform.trim()) {
    ElMessage.warning(t('community.formRequired'))
    return
  }
  try {
    const { data } = await analyticsAPI.submitReference({
      source_url: refForm.source_url.trim(),
      source_platform: refForm.source_platform.trim() })
    if (data.duplicate) ElMessage.info(t('community.refDuplicate'))
    else ElMessage.success(t('community.refSubmitted'))
    refForm.source_url = ''
    refForm.source_platform = ''
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('community.sendFailed'))
  }
}

onMounted(() => loadPosts(1))
</script>

<style scoped>
.community-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 4px 0 24px;
}

.page-hero { text-align: center; padding: 24px 20px 6px; }

.hero-title {
  margin: 0 0 10px;
  font-size: 30px;
  font-weight: 800;
  color: var(--text-primary);
}

.hero-subtitle {
  margin: 0 auto;
  max-width: 560px;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
}

.community-layout {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 18px;
  align-items: start;
}

/* 帖子卡片 */
.post-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 14px;
  transition: border-color 0.22s ease;
}

.post-card:hover { border-color: rgba(74,222,128,0.3); }

.post-head { display: flex; align-items: center; gap: 10px; }

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--accent-bg);
  color: var(--accent);
  font-weight: 800;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.post-meta { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.post-name { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.post-time { font-size: 11px; color: var(--text-muted); }

.post-content {
  margin: 10px 0 8px;
  font-size: 13.5px;
  color: var(--text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
}

.post-actions { display: flex; gap: 14px; }

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover { color: var(--accent); border-color: rgba(74,222,128,0.4); }
.action-btn.liked { color: var(--accent); border-color: var(--accent);
  background: var(--accent-bg); }
.action-btn.danger:hover { color: #fb7185; border-color: rgba(251,113,133,0.4); }

/* 回复 */
.reply-list {
  margin-top: 12px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.02);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reply-item { border-left: 2px solid var(--border-color); padding-left: 10px; }
.reply-head { display: flex; gap: 10px; align-items: baseline; }
.reply-name { font-size: 12px; font-weight: 700; color: var(--text-primary); }
.reply-time { font-size: 11px; color: var(--text-muted); }
.reply-content { margin: 3px 0 0; font-size: 12.5px;
  color: var(--text-secondary); line-height: 1.6; }

.reply-box { margin-top: 12px; }
.reply-name-input { margin-bottom: 8px; max-width: 220px; }
.reply-input-row { display: flex; gap: 8px; }

.pagination { text-align: center; margin-top: 6px; }

/* 侧栏 */
.side-column { display: flex; flex-direction: column; gap: 14px; }

.side-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.side-title { margin: 0; font-size: 14px; font-weight: 700;
  color: var(--text-primary); }
.side-desc { margin: 0; font-size: 12px; color: var(--text-muted);
  line-height: 1.6; }
.form-item { width: 100%; }
.submit-btn { align-self: flex-start; }

.empty-hint {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
}

@media (max-width: 900px) {
  .community-layout { grid-template-columns: 1fr; }
}
</style>
