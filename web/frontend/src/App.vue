<template>
  <div class="app-container">
    <!-- 左侧边栏：API配置 -->
    <aside class="sidebar">
      <ConfigPanel @config-saved="onConfigSaved" />
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 上部：文件上传 + 文本输入 -->
      <UploadZone @file-selected="onFileSelected" @excel-processed="onExcelProcessed" />
      <div class="card">
        <div class="card-header">📝 文本输入</div>
        <textarea
          v-model="textInput"
          class="form-textarea"
          placeholder="粘贴专利文本（包含摘要或权利要求）..."
        ></textarea>
        <div style="margin-top: 12px;">
          <button
            class="btn btn-primary"
            @click="classifyText"
            :disabled="!textInput.trim() || loading"
          >
            {{ loading ? '分类中...' : '开始分类' }}
          </button>
        </div>
      </div>

      <!-- 下部：分类结果展示 -->
      <ResultDisplay :result="result" :batchResults="batchResults" :loading="loading" />

      <!-- 底部：规则树 -->
      <RuleTree :rules="rules" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ConfigPanel from './components/ConfigPanel.vue'
import UploadZone from './components/UploadZone.vue'
import ResultDisplay from './components/ResultDisplay.vue'
import RuleTree from './components/RuleTree.vue'

// 状态
const textInput = ref('')
const result = ref(null)
const batchResults = ref([])
const loading = ref(false)
const rules = ref([])
const configSaved = ref(false)

// 获取规则
async function fetchRules() {
  try {
    const res = await fetch('/api/rules')
    const data = await res.json()
    if (data.success) {
      rules.value = data.rules
    }
  } catch (e) {
    console.error('获取规则失败:', e)
  }
}

// 单条文本分类
async function classifyText() {
  if (!textInput.value.trim()) return

  loading.value = true
  result.value = null
  batchResults.value = []

  try {
    const res = await fetch('/api/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: textInput.value })
    })
    const data = await res.json()
    result.value = data
  } catch (e) {
    result.value = {
      success: false,
      error: '请求失败: ' + e.message
    }
  } finally {
    loading.value = false
  }
}

// 文件上传分类
async function onFileSelected(file) {
  loading.value = true
  result.value = null
  batchResults.value = []

  try {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch('/api/upload/file', {
      method: 'POST',
      body: formData
    })
    const data = await res.json()

    if (data.success) {
      // 用解析出的文本进行分类
      textInput.value = data.text.slice(0, 5000) // 截取前5000字符
      await classifyText()
    } else {
      result.value = {
        success: false,
        error: data.error || '文件解析失败'
      }
    }
  } catch (e) {
    result.value = {
      success: false,
      error: '上传失败: ' + e.message
    }
  } finally {
    loading.value = false
  }
}

// Excel批量分类
async function onExcelProcessed(excelData) {
  loading.value = true
  result.value = null
  batchResults.value = []

  try {
    const res = await fetch('/api/classify/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts: excelData.texts })
    })
    const data = await res.json()

    if (data.success) {
      batchResults.value = data.results || []
    } else {
      result.value = {
        success: false,
        error: data.error || '批量分类失败'
      }
    }
  } catch (e) {
    result.value = {
      success: false,
      error: '批量分类失败: ' + e.message
    }
  } finally {
    loading.value = false
  }
}

// 配置保存回调
function onConfigSaved() {
  configSaved.value = true
}

// 初始化
onMounted(() => {
  fetchRules()
})
</script>