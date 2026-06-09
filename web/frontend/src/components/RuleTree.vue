<template>
  <div class="card" v-if="rules.length > 0">
    <div class="card-header">
      🌳 分类规则树
      <span style="color: var(--text-secondary); font-size: 12px;">
        共 {{ totalNodes }} 个分支
      </span>
    </div>
    <div class="rule-tree">
      <RuleTreeNode
        v-for="node in rules"
        :key="node.branch_id"
        :node="node"
        :expanded="expandedIds.includes(node.branch_id)"
        :selected-id="selectedId"
        :expanded-ids="expandedIds"
        @toggle="toggleExpand"
        @select="onSelect"
      />
    </div>
  </div>
  <div class="card" v-else>
    <div class="card-header">🌳 分类规则树</div>
    <div style="color: var(--text-secondary); font-size: 14px;">
      未加载任何分类规则，请检查 rules/ 目录
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import RuleTreeNode from './RuleTreeNode.vue'

const props = defineProps({
  rules: {
    type: Array,
    default: () => []
  }
})

const expandedIds = ref([])
const selectedId = ref(null)

// 计算总节点数
const totalNodes = computed(() => {
  let count = 0
  function countNodes(nodes) {
    for (const node of nodes) {
      count++
      if (node.children && node.children.length > 0) {
        countNodes(node.children)
      }
    }
  }
  countNodes(props.rules)
  return count
})

function toggleExpand(branchId) {
  const index = expandedIds.value.indexOf(branchId)
  if (index >= 0) {
    expandedIds.value.splice(index, 1)
  } else {
    expandedIds.value.push(branchId)
  }
}

function onSelect(branchId) {
  selectedId.value = branchId
}
</script>