<template>
  <div class="card">
    <div class="card-header">⚙️ API 配置</div>

    <div class="form-group">
      <label class="form-label">服务商</label>
      <select v-model="config.provider" class="form-select" @change="onProviderChange">
        <option value="openai">OpenAI</option>
        <option value="deepseek">DeepSeek</option>
        <option value="zhipu">智谱AI</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">API Key</label>
      <div style="position: relative;">
        <input
          v-model="config.apiKey"
          :type="showKey ? 'text' : 'password'"
          class="form-input"
          :placeholder="hasSavedKey ? '已保存，留空则不修改' : '输入API Key...'"
          style="padding-right: 60px;"
        />
        <button
          @click="showKey = !showKey"
          style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; color: var(--text-secondary); font-size: 12px;"
        >
          {{ showKey ? '隐藏' : '显示' }}
        </button>
      </div>
      <div v-if="hasSavedKey" style="font-size: 12px; color: var(--success-color, #52c41a); margin-top: 4px;">
        ✓ 已保存 ({{ savedKeyMasked }})，留空则保留原Key
      </div>
    </div>

    <div class="form-group" v-if="config.provider === 'openai'">
      <label class="form-label">API Base URL</label>
      <input
        v-model="config.apiBase"
        type="text"
        class="form-input"
        placeholder="https://api.openai.com"
      />
    </div>

    <div class="form-group">
      <label class="form-label">模型</label>
      <select v-model="config.model" class="form-select">
        <option v-for="m in currentModelOptions" :key="m.value" :value="m.value">{{ m.label }}</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">置信度阈值</label>
      <input
        v-model.number="config.confidenceThreshold"
        type="number"
        class="form-input"
        min="0"
        max="1"
        step="0.1"
      />
      <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
        分类置信度低于此值时标记为"需人工审核"，默认0.6
      </div>
    </div>

    <div style="margin-top: 16px;">
      <button class="btn btn-primary" @click="saveConfig" :disabled="saving">
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
    </div>

    <div v-if="message" :class="messageType === 'success' ? 'success-message' : 'error-message'" style="margin-top: 12px;">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const emit = defineEmits(['config-saved'])

// 模型选项定义
const MODEL_OPTIONS = {
  openai: [
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini (推荐)' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' }
  ],
  deepseek: [
    { value: 'deepseek/deepseek-chat', label: 'DeepSeek V3 (通用)' },
    { value: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro' },
    { value: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash (快速)' }
  ],
  zhipu: [
    { value: 'zhipu/glm-4-flash', label: 'GLM-4 Flash (推荐分类)' },
    { value: 'zhipu/glm-4', label: 'GLM-4' },
    { value: 'zhipu/glm-4-plus', label: 'GLM-4 Plus' },
    { value: 'zhipu/glm-4.7-flash', label: 'GLM-4.7 Flash (免费)' },
    { value: 'zhipu/glm-5', label: 'GLM-5 (思考模型，不适合分类)' }
  ]
}

// 配置状态
const config = ref({
  provider: 'openai',
  apiKey: '',
  apiBase: 'https://api.openai.com',
  model: 'gpt-4o-mini',
  confidenceThreshold: 0.6
})

const saving = ref(false)
const message = ref('')
const messageType = ref('success')
const showKey = ref(false)
const hasSavedKey = ref(false)
const savedKeyMasked = ref('')

// 当前服务商的模型选项
const currentModelOptions = computed(() => {
  return MODEL_OPTIONS[config.value.provider] || MODEL_OPTIONS.openai
})

// 服务商变更时更新默认模型
function onProviderChange() {
  const options = currentModelOptions.value
  if (options.length > 0) {
    config.value.model = options[0].value
  }
  if (config.value.provider !== 'openai') {
    config.value.apiBase = ''
  } else {
    config.value.apiBase = 'https://api.openai.com'
  }
  // 切换服务商时重置Key状态
  hasSavedKey.value = false
  savedKeyMasked.value = ''
}

// 加载当前配置
async function loadConfig() {
  try {
    const res = await fetch('/api/config')
    const data = await res.json()
    config.value.provider = data.provider || 'openai'
    config.value.apiBase = data.api_base || 'https://api.openai.com'
    config.value.model = data.model || 'gpt-4o-mini'
    config.value.confidenceThreshold = data.confidence_threshold || 0.6
    // 记录已保存的Key状态
    if (data.api_key_masked && data.api_key_masked !== '****') {
      hasSavedKey.value = true
      savedKeyMasked.value = data.api_key_masked
    }
  } catch (e) {
    console.error('加载配置失败:', e)
  }
}

// 保存配置
async function saveConfig() {
  saving.value = true
  message.value = ''

  try {
    const body = {
      provider: config.value.provider,
      api_key: config.value.apiKey,
      api_base: config.value.apiBase,
      model: config.value.model,
      confidence_threshold: config.value.confidenceThreshold
    }

    // 如果Key为空且之前有保存过，告诉后端保留原Key
    if (!body.api_key && hasSavedKey.value) {
      body.keep_existing_key = true
    }

    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await res.json()

    if (data.success) {
      message.value = data.message || '配置已保存'
      messageType.value = 'success'
      // 更新保存状态
      if (body.api_key) {
        hasSavedKey.value = true
        savedKeyMasked.value = body.api_key.slice(0, 4) + '****' + body.api_key.slice(-4)
        config.value.apiKey = ''  // 清空输入框
      }
      emit('config-saved')
    } else {
      message.value = data.detail || '保存失败'
      messageType.value = 'error'
    }
  } catch (e) {
    message.value = '请求失败: ' + e.message
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

// 初始化
onMounted(() => {
  loadConfig()
})
</script>
