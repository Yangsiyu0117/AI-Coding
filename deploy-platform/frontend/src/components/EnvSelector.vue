<template>
  <div class="env-selector">
    <el-select
      v-model="envId"
      placeholder="选择环境"
      :loading="envStore.loading"
      @change="onChange"
    >
      <el-option
        v-for="env in envStore.environments"
        :key="env.id"
        :label="env.name"
        :value="env.id"
      />
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useEnvironmentStore } from '../stores/environment'

const envStore = useEnvironmentStore()
const envId = ref(envStore.currentEnvId)

onMounted(() => {
  envStore.loadEnvironments()
})

function onChange(val: number) {
  const env = envStore.environments.find((e) => e.id === val)
  if (env) envStore.selectEnv(env.id, env.name)
}
</script>
