<template>
  <div>
    <div
      class="rule-tree-node"
      :class="{ active: selectedId === node.branch_id }"
      @click.stop="onSelect"
    >
      <span v-if="node.children && node.children.length > 0" @click.stop="onToggle" style="cursor: pointer; margin-right: 4px;">
        {{ expanded ? '▼' : '▶' }}
      </span>
      <span v-else style="margin-right: 4px;">•</span>
      <span>{{ node.branch_name }}</span>
      <span style="color: var(--text-secondary); font-size: 12px; margin-left: 4px;">
        ({{ node.branch_id }})
      </span>
    </div>
    <div v-if="expanded && node.children && node.children.length > 0" style="padding-left: 16px;">
      <RuleTreeNode
        v-for="child in node.children"
        :key="child.branch_id"
        :node="child"
        :expanded="expandedIds.includes(child.branch_id)"
        :selected-id="selectedId"
        :expanded-ids="expandedIds"
        @toggle="$emit('toggle', $event)"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  expanded: {
    type: Boolean,
    default: false
  },
  selectedId: {
    type: String,
    default: null
  },
  expandedIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['toggle', 'select'])

function onToggle() {
  emit('toggle', props.node.branch_id)
}

function onSelect() {
  emit('select', props.node.branch_id)
}
</script>