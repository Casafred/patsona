<template>
  <div class="card" v-if="loading || result || batchResults.length > 0">
    <div class="card-header">📊 分类结果</div>

    <!-- 加载状态 -->
    <div class="loading" v-if="loading">
      <div class="loading-spinner"></div>
      <div style="text-align: center; margin-top: 8px; color: var(--text-secondary);">
        正在分类中...
      </div>
    </div>

    <!-- 批量结果 -->
    <div v-else-if="batchResults.length > 0">
      <div class="batch-summary">
        共 {{ batchResults.length }} 条结果
        <span class="batch-warning-count" v-if="reviewCount > 0">
          ({{ reviewCount }} 条需审核)
        </span>
      </div>

      <div class="batch-table">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>分类分支</th>
              <th>置信度</th>
              <th>状态</th>
              <th>判定依据</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in batchResults" :key="item.index">
              <td>{{ item.index + 1 }}</td>
              <td>{{ item.branch_name }}</td>
              <td>
                <div class="mini-progress">
                  <div class="mini-progress-fill" :style="{ width: (item.confidence * 100) + '%' }"></div>
                  <span>{{ (item.confidence * 100).toFixed(0) }}%</span>
                </div>
              </td>
              <td>
                <span class="mini-tag" :class="item.needs_review ? 'tag-warning' : 'tag-success'">
                  {{ item.needs_review ? '审核' : '确定' }}
                </span>
              </td>
              <td class="reasoning-cell">{{ item.reasoning.slice(0, 50) }}...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 单条结果错误 -->
    <div class="error-message" v-else-if="result && !result.success">
      {{ result.error }}
    </div>

    <!-- 单条成功结果 -->
    <div v-else-if="result && result.success">
      <!-- 最终分类 -->
      <div class="result-item">
        <div class="result-header">
          <div class="result-title">
            {{ result.branch_name }}
            <span class="status-tag" :class="result.needs_review ? 'status-warning' : 'status-success'">
              {{ result.needs_review ? '需审核' : '已确定' }}
            </span>
          </div>
          <div class="result-confidence">
            置信度: {{ (result.confidence * 100).toFixed(1) }}%
          </div>
        </div>

        <!-- 置信度进度条 -->
        <div class="progress-bar" style="margin-top: 8px;">
          <div
            class="progress-fill"
            :style="{ width: (result.confidence * 100) + '%' }"
          ></div>
        </div>

        <!-- 判定依据 -->
        <div class="result-reasoning" v-if="result.reasoning">
          {{ result.reasoning }}
        </div>
      </div>

      <!-- 分层过程 -->
      <div style="margin-top: 16px;">
        <div class="card-header">分层分类过程</div>
        <div v-for="layer in result.layer_results" :key="layer.layer_name" class="layer-result">
          <div class="layer-name">{{ layer.layer_name }}</div>
          <div class="layer-detail">{{ layer.detail }}</div>
          <div class="layer-candidates">
            候选分支: {{ layer.candidate_names.join(', ') || '无' }}
            <span v-if="layer.confidence > 0">
              (置信度: {{ (layer.confidence * 100).toFixed(1) }}%)
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    default: null
  },
  batchResults: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const reviewCount = computed(() => {
  return props.batchResults.filter(r => r.needs_review).length
})
</script>

<style scoped>
.batch-summary {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.batch-warning-count {
  color: #f59e0b;
}

.batch-table {
  overflow-x: auto;
}

.batch-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.batch-table th,
.batch-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.batch-table th {
  background: var(--bg-color);
  font-weight: 600;
}

.mini-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-progress-fill {
  height: 4px;
  background: var(--primary-color);
  border-radius: 2px;
  min-width: 20px;
}

.mini-tag {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}

.tag-success {
  background: #10b98120;
  color: #10b981;
}

.tag-warning {
  background: #f59e0b20;
  color: #f59e0b;
}

.reasoning-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-secondary);
}
</style>