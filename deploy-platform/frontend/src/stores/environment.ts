import { ref } from 'vue'
import { defineStore } from 'pinia'
import { fetchEnvironments, type Environment } from '../api/environments'

export const useEnvironmentStore = defineStore('environment', () => {
  const environments = ref<Environment[]>([])
  const loading = ref(false)
  const currentEnvId = ref<number | null>(null)
  const currentEnvName = ref('')

  async function loadEnvironments() {
    loading.value = true
    try {
      environments.value = await fetchEnvironments()
      if (environments.value.length > 0 && currentEnvId.value === null) {
        const first = environments.value[0]
        selectEnv(first.id, first.name)
      }
    } finally {
      loading.value = false
    }
  }

  function selectEnv(id: number, name: string) {
    currentEnvId.value = id
    currentEnvName.value = name
  }

  return { environments, loading, currentEnvId, currentEnvName, loadEnvironments, selectEnv }
})
