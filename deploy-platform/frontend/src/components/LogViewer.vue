<template>
  <div class="log-viewer" ref="containerRef">
    <div class="log-header">
      <span class="log-dot" />
      <span class="log-title">日志输出</span>
    </div>

    <!-- Search and filter toolbar -->
    <div v-if="logContent" class="log-toolbar">
      <el-input
        v-model="searchText"
        placeholder="搜索日志关键字..."
        clearable
        size="small"
        class="search-input"
      />
      <el-radio-group v-model="filterLevel" size="small" class="filter-radio">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="ERROR">ERROR</el-radio-button>
        <el-radio-button value="WARN">WARN</el-radio-button>
        <el-radio-button value="INFO">INFO</el-radio-button>
      </el-radio-group>
      <span class="line-count">共 {{ displayedLines.length }} 行</span>
    </div>

    <pre v-if="logContent" v-html="highlightedLog"></pre>
    <div v-else class="empty-hint">选择左侧步骤查看日志</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

const props = withDefaults(defineProps<{
  logContent: string
  autoScroll?: boolean
}>(), {
  autoScroll: true,
})

const containerRef = ref<HTMLElement>()
const searchText = ref('')
const filterLevel = ref('')

watch(
  () => props.logContent,
  () => {
    // Reset search and filter when log content changes
    searchText.value = ''
    filterLevel.value = ''
    if (props.autoScroll) {
      nextTick(() => {
        const el = containerRef.value
        if (el) {
          el.scrollTop = el.scrollHeight
        }
      })
    }
  },
)

const lines = computed(() => {
  if (!props.logContent) return []
  return props.logContent.split('\n')
})

const displayedLines = computed(() => {
  let result = lines.value
  // Filter by level first
  if (filterLevel.value) {
    const keyword = filterLevel.value.toUpperCase()
    result = result.filter((line) => {
      const upper = line.toUpperCase()
      return upper.includes(keyword)
    })
  }
  // Then filter by search text
  if (searchText.value.trim()) {
    const search = searchText.value.trim().toLowerCase()
    result = result.filter((line) => line.toLowerCase().includes(search))
  }
  return result
})

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

const highlightedLog = computed(() => {
  const lines = displayedLines.value
  if (!searchText.value.trim()) {
    return escapeHtml(lines.join('\n'))
  }
  const search = searchText.value.trim()
  // Escape special regex characters in search term
  const escapedSearch = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escapedSearch})`, 'gi')
  return lines
    .map((line) => {
      return escapeHtml(line).replace(
        regex,
        (match) => `<mark>${match}</mark>`,
      )
    })
    .join('\n')
})
</script>

<style scoped>
.log-viewer {
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 6px;
  height: 100%;
  min-height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.5;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.log-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.5);
}

.log-title {
  font-size: 13px;
  color: #aaa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.log-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.search-input {
  width: 220px;
}

.search-input :deep(.el-input__inner) {
  background: #2d2d2d;
  border-color: rgba(255, 255, 255, 0.12);
  color: #d4d4d4;
}

.search-input :deep(.el-input__inner)::placeholder {
  color: #666;
}

.filter-radio {
  flex-shrink: 0;
}

.filter-radio :deep(.el-radio-button__inner) {
  background: #2d2d2d;
  border-color: rgba(255, 255, 255, 0.12);
  color: #999;
  font-size: 12px;
  padding: 4px 10px;
}

.filter-radio :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.line-count {
  color: #888;
  font-size: 12px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin-left: auto;
  white-space: nowrap;
}

.log-viewer pre {
  margin: 0;
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}

.log-viewer pre :deep(mark) {
  background: #ffeb3b;
  color: #1e1e1e;
  padding: 1px 2px;
  border-radius: 2px;
}

.empty-hint {
  color: #666;
  text-align: center;
  padding-top: 100px;
}
</style>
