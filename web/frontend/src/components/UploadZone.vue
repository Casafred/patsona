<template>
  <div class="card">
    <div class="card-header">📁 文件上传</div>
    <div
      class="upload-zone"
      :class="{ dragging: isDragging }"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      @click="triggerUpload"
    >
      <div class="upload-zone-icon">📄</div>
      <div class="upload-zone-text">
        {{ isDragging ? '松开鼠标上传文件' : '拖拽文件到此处或点击上传' }}
      </div>
      <div class="upload-zone-hint">支持 PDF、Word、TXT、Excel 格式</div>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept=".pdf,.docx,.doc,.txt,.xlsx,.xls"
      style="display: none"
      @change="onFileChange"
    />
    <div v-if="selectedFile" style="margin-top: 12px; font-size: 14px;">
      已选择: {{ selectedFile.name }}
    </div>

    <!-- Excel列选择面板 -->
    <div v-if="isExcel && excelColumns.length > 0" class="excel-panel">
      <div class="excel-panel-header">📊 Excel列配置</div>
      <div class="excel-info">检测到 {{ excelRowCount }} 行数据</div>

      <div class="form-group">
        <label class="form-label">选择要拼接的列（按顺序拼接为完整文本）</label>
        <div class="column-checkboxes">
          <label v-for="col in excelColumns" :key="col" class="checkbox-label">
            <input type="checkbox" v-model="selectedColumns" :value="col" />
            {{ col }}
          </label>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">列分隔符</label>
        <select v-model="columnSeparator" class="form-select">
          <option value=" ">空格</option>
          <option value="\n">换行</option>
          <option value=";">分号</option>
          <option value=",">逗号</option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">预览（第一行拼接结果）</label>
        <div class="preview-box">{{ previewText }}</div>
      </div>

      <button class="btn btn-primary" @click="processExcel" :disabled="selectedColumns.length === 0">
        开始批量分类
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const emit = defineEmits(['file-selected', 'excel-processed'])

const fileInput = ref(null)
const isDragging = ref(false)
const selectedFile = ref(null)
const isExcel = ref(false)
const excelColumns = ref([])
const excelData = ref([])
const excelRowCount = ref(0)
const selectedColumns = ref([])
const columnSeparator = ref(' ')
const previewText = ref('')

function triggerUpload() {
  fileInput.value.click()
}

function onDragOver() {
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onDrop(e) {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

function onFileChange(e) {
  const files = e.target.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

async function handleFile(file) {
  const suffix = file.name.split('.').pop().toLowerCase()
  const validSuffixes = ['pdf', 'docx', 'doc', 'txt', 'xlsx', 'xls']

  if (!validSuffixes.includes(suffix)) {
    alert('不支持的文件格式')
    return
  }

  selectedFile.value = file
  isExcel.value = suffix === 'xlsx' || suffix === 'xls'

  if (isExcel.value) {
    // 上传Excel获取列信息
    await uploadExcelForColumns(file)
  } else {
    emit('file-selected', file)
  }
}

async function uploadExcelForColumns(file) {
  try {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch('/api/upload/excel-info', {
      method: 'POST',
      body: formData
    })
    const data = await res.json()

    if (data.success) {
      excelColumns.value = data.columns || []
      excelRowCount.value = data.row_count || 0
      excelData.value = data.sample_data || []
      // 默认选择所有列
      selectedColumns.value = excelColumns.value.slice(0, 3)
    } else {
      alert(data.error || '解析Excel失败')
    }
  } catch (e) {
    alert('上传Excel失败: ' + e.message)
  }
}

// 计算预览文本
watch([selectedColumns, columnSeparator, excelData], () => {
  if (excelData.value.length > 0 && selectedColumns.value.length > 0) {
    const firstRow = excelData.value[0]
    previewText.value = selectedColumns.value
      .map(col => firstRow[col] || '')
      .join(columnSeparator.value === '\n' ? '\n' : columnSeparator.value)
      .slice(0, 200) + '...'
  } else {
    previewText.value = ''
  }
}, { immediate: true })

async function processExcel() {
  if (selectedColumns.value.length === 0) return

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('columns', JSON.stringify(selectedColumns.value))
    formData.append('separator', columnSeparator.value)

    const res = await fetch('/api/upload/excel-process', {
      method: 'POST',
      body: formData
    })
    const data = await res.json()

    if (data.success) {
      emit('excel-processed', {
        texts: data.texts,
        rowCount: data.row_count
      })
    } else {
      alert(data.error || '处理Excel失败')
    }
  } catch (e) {
    alert('处理Excel失败: ' + e.message)
  }
}
</script>

<style scoped>
.excel-panel {
  margin-top: 16px;
  padding: 16px;
  background: var(--card-bg);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.excel-panel-header {
  font-weight: 600;
  margin-bottom: 12px;
}

.excel-info {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.column-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  cursor: pointer;
}

.checkbox-label input {
  cursor: pointer;
}

.preview-box {
  background: var(--bg-color);
  padding: 12px;
  border-radius: 4px;
  font-size: 13px;
  color: var(--text-secondary);
  max-height: 100px;
  overflow-y: auto;
  white-space: pre-wrap;
}
</style>