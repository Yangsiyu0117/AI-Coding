<template>
  <el-card class="service-card">
    <template #header>
      <span>{{ serviceName }}</span>
      <el-tag :type="statusColor" size="small">{{ statusText }}</el-tag>
    </template>
    <p>在线: {{ healthyNodes }} / {{ totalNodes }}</p>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  serviceName: string
  healthyNodes: number
  totalNodes: number
}>()

const statusColor = computed(() => (props.healthyNodes === props.totalNodes ? 'success' : 'danger'))
const statusText = computed(() => (props.healthyNodes === props.totalNodes ? '正常' : '异常'))
</script>
