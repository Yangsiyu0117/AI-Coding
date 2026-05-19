import React, { useState, useEffect, useCallback } from 'react'
import {
  Settings, Server, Bell, Play, FileText, ChevronRight, Plus, Trash2,
  CheckCircle, AlertTriangle, XCircle, Eye, TestTube,
  RefreshCw, Database, Shield, Mail, MessageSquare, Layers, Edit3, Clock
} from 'lucide-react'

const API_BASE = '/api'

const AVAILABLE_PLUGINS = [
  { name: 'node_exporter', label: '系统指标 (Node)', description: 'CPU/内存/磁盘/网络/负载', defaultPattern: 'node' },
  { name: 'process_exporter', label: '进程监控 (Process)', description: '进程存活/资源占用', defaultPattern: 'process' },
  { name: 'cadvisor', label: '容器监控 (cAdvisor)', description: 'Docker容器资源', defaultPattern: 'cadvisor|docker' },
  { name: 'mysqld_exporter', label: 'MySQL', description: '连接数/慢查询/复制/缓冲池', defaultPattern: 'mysql' },
  { name: 'redis_exporter', label: 'Redis', description: '内存/连接/命中率/持久化', defaultPattern: 'redis' },
  { name: 'elasticsearch', label: 'Elasticsearch', description: '集群状态/索引/JVM', defaultPattern: 'elasticsearch|es' },
  { name: 'etcd', label: 'etcd', description: '集群健康/Leader/延迟', defaultPattern: 'etcd' },
  { name: 'pulsar', label: 'Pulsar', description: '消息积压/吞吐/存储', defaultPattern: 'pulsar' },
  { name: 'minio', label: 'MinIO', description: '存储空间/请求/健康', defaultPattern: 'minio' },
  { name: 'apisix', label: 'APISIX', description: '请求QPS/延迟/错误率', defaultPattern: 'apisix' },
  { name: 'generic', label: '自定义查询 (Generic)', description: '自定义PromQL查询', defaultPattern: '.*' },
]

const REPORT_FORMATS = [
  { value: 'feishu_card', label: '飞书卡片' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'html', label: 'HTML' },
  { value: 'text', label: '纯文本' },
  { value: 'json', label: 'JSON' },
]

async function apiFetch(url, options = {}) {
  const resp = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: resp.statusText }))
    throw new Error(err.error || 'Request failed')
  }
  return resp.json()
}

export default function PatrolDashboard() {
  const [activeTab, setActiveTab] = useState('projects')
  const [selectedProject, setSelectedProject] = useState(null)
  const [showModal, setShowModal] = useState(null)
  const [editingProject, setEditingProject] = useState(null)
  const [editingChannel, setEditingChannel] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Data states
  const [projects, setProjects] = useState([])
  const [pluginConfigs, setPluginConfigs] = useState([])
  const [channels, setChannels] = useState([])
  const [records, setRecords] = useState([])
  const [discoveredJobs, setDiscoveredJobs] = useState(null)
  const [reportData, setReportData] = useState({ html: '', markdown: '', summary: null })
  const [reportFormat, setReportFormat] = useState('html')
  const [stats, setStats] = useState({ total_projects: 0, total_records: 0, recent_records: 0, abnormal_today: 0 })
  const [settings, setSettings] = useState({ records_retention_days: '90', details_retention_days: '90' })
  const [savingSettings, setSavingSettings] = useState(false)
  const [metricEditorIdx, setMetricEditorIdx] = useState(null)
  const [datasources, setDatasources] = useState([])
  const [notificationLogs, setNotificationLogs] = useState([])
  const [schedules, setSchedules] = useState([])
  const [recordFilter, setRecordFilter] = useState('all')
  const [editingSchedule, setEditingSchedule] = useState(null)

  // Project form state
  const [newProject, setNewProject] = useState({
    name: '', env: 'production', prometheus_url: '',
    auth_enabled: false, auth_username: '', auth_password: '', description: ''
  })

  // Channel form state
  const [newChannel, setNewChannel] = useState({ channel_type: 'feishu', report_format: 'markdown', config: {} })

  const openAddChannel = () => {
    setNewChannel({ channel_type: 'feishu', report_format: 'markdown', config: {} })
    setShowModal('addChannel')
  }

  const closeChannelModal = () => {
    setNewChannel({ channel_type: 'feishu', report_format: 'markdown', config: {} })
    setEditingChannel(null)
    setShowModal(null)
  }

  // Notifications
  const showError = (msg) => { setError(msg); setTimeout(() => setError(null), 4000) }
  const showSuccess = (msg) => { setSuccess(msg); setTimeout(() => setSuccess(null), 3000) }

  // Load projects
  const loadProjects = useCallback(async () => {
    try {
      const data = await apiFetch('/projects')
      setProjects(data)
    } catch (e) { showError('加载项目列表失败: ' + e.message) }
  }, [])

  const loadStats = useCallback(async () => {
    try {
      const data = await apiFetch('/stats/overview')
      setStats(data)
    } catch (e) { /* ignore */ }
  }, [])

  const loadSettings = useCallback(async () => {
    try {
      const data = await apiFetch('/settings')
      setSettings({ records_retention_days: '90', details_retention_days: '90', ...data })
    } catch (e) { /* ignore */ }
  }, [])

  const loadDatasources = async (projectId) => {
    try {
      const data = await apiFetch(`/projects/${projectId}/datasources`)
      setDatasources(data)
    } catch (e) { /* ignore */ }
  }

  const loadNotificationLogs = async (projectId) => {
    try {
      const data = await apiFetch(`/projects/${projectId}/notification-logs`)
      setNotificationLogs(data)
    } catch (e) { /* ignore */ }
  }

  const loadSchedules = async (projectId) => {
    try {
      const data = await apiFetch(`/projects/${projectId}/schedules`)
      setSchedules(data)
    } catch (e) { /* ignore */ }
  }

  const deleteNotificationLog = async (logId) => {
    if (!selectedProject) return
    try {
      await apiFetch(`/notification-logs/${logId}`, { method: 'DELETE' })
      showSuccess('日志已删除')
      loadNotificationLogs(selectedProject.id)
    } catch (e) { showError('删除失败: ' + e.message) }
  }

  const saveSchedule = async () => {
    if (!selectedProject) return
    try {
      const isEdit = editingSchedule?.id
      const url = isEdit
        ? `/projects/${selectedProject.id}/schedules/${editingSchedule.id}`
        : `/projects/${selectedProject.id}/schedules`
      await apiFetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        body: JSON.stringify(editingSchedule)
      })
      showSuccess('定时任务已保存')
      setShowModal(null)
      setEditingSchedule(null)
      loadSchedules(selectedProject.id)
    } catch (e) { showError('保存失败: ' + e.message) }
  }

  const deleteSchedule = async (scheduleId) => {
    if (!selectedProject || !confirm('确定删除此定时任务？')) return
    try {
      await apiFetch(`/projects/${selectedProject.id}/schedules/${scheduleId}`, { method: 'DELETE' })
      showSuccess('定时任务已删除')
      loadSchedules(selectedProject.id)
    } catch (e) { showError('删除失败: ' + e.message) }
  }

  const toggleSchedule = async (schedule) => {
    if (!selectedProject) return
    try {
      await apiFetch(`/projects/${selectedProject.id}/schedules/${schedule.id}`, {
        method: 'PUT',
        body: JSON.stringify({ ...schedule, enabled: !schedule.enabled })
      })
      loadSchedules(selectedProject.id)
    } catch (e) { showError('更新失败: ' + e.message) }
  }

  useEffect(() => {
    loadProjects()
    loadStats()
    loadSettings()
  }, [loadProjects, loadStats, loadSettings])

  // Project selection
  const selectProject = async (project) => {
    setSelectedProject(project)
    setDiscoveredJobs(null)
    setActiveTab('plugins')
    loadPlugins(project.id)
    loadChannels(project.id)
    loadRecords(project.id)
    loadDatasources(project.id)
    loadNotificationLogs(project.id)
    loadSchedules(project.id)
  }

  // Plugins
  const loadPlugins = async (projectId) => {
    try {
      const data = await apiFetch(`/projects/${projectId}/plugins`)
      if (data.length > 0) {
        setPluginConfigs(data.map(d => ({
          ...d,
          thresholds: JSON.parse(d.thresholds_json || '{}'),
          extra_config: JSON.parse(d.extra_config_json || '{}'),
          filter_config: JSON.parse(d.filter_config_json || '{}'),
          datasource_id: d.datasource_id || null,
        })))
      } else {
        setPluginConfigs([
          { plugin_name: 'node_exporter', enabled: true, job_pattern: 'node', thresholds: { cpu_usage_percent: 85, memory_usage_percent: 85, disk_usage_percent: 90 }, extra_config: {}, datasource_id: null, filter_config: {} },
          { plugin_name: 'mysqld_exporter', enabled: true, job_pattern: 'mysql', thresholds: { connections_usage_percent: 80, slow_queries_per_min: 10 }, extra_config: {}, datasource_id: null, filter_config: {} },
          { plugin_name: 'redis_exporter', enabled: true, job_pattern: 'redis', thresholds: { memory_usage_percent: 80 }, extra_config: {}, datasource_id: null, filter_config: {} },
          { plugin_name: 'cadvisor', enabled: true, job_pattern: 'cadvisor|docker', thresholds: {}, extra_config: {}, datasource_id: null, filter_config: {} },
        ])
      }
    } catch (e) { showError('加载插件配置失败') }
  }

  const savePlugins = async () => {
    if (!selectedProject) return
    try {
      await apiFetch(`/projects/${selectedProject.id}/plugins`, {
        method: 'POST',
        body: JSON.stringify({
          plugins: pluginConfigs.map(p => ({
            plugin_name: p.plugin_name,
            enabled: p.enabled ? 1 : 0,
            job_pattern: p.job_pattern,
            thresholds: p.thresholds || {},
            extra_config: p.extra_config || {},
            datasource_id: p.datasource_id || null,
            filter_config: p.filter_config || {},
          }))
        })
      })
      showSuccess('插件配置保存成功')
    } catch (e) { showError('保存插件配置失败') }
  }

  const handleDiscover = async () => {
    if (!selectedProject) return
    setLoading(true)
    try {
      const data = await apiFetch(`/projects/${selectedProject.id}/discover`)
      setDiscoveredJobs(data.jobs)
      showSuccess(`已发现 ${Object.keys(data.jobs).length} 个Job`)
    } catch (e) { showError('发现Targets失败: ' + e.message) }
    setLoading(false)
  }

  // Channels
  const loadChannels = async (projectId) => {
    try {
      const data = await apiFetch(`/projects/${projectId}/channels`)
      setChannels(data)
    } catch (e) { /* ignore */ }
  }

  // Channel CRUD
  const deleteChannel = async (channelId) => {
    if (!selectedProject || !confirm('确定删除此通知渠道？')) return
    try {
      await apiFetch(`/projects/${selectedProject.id}/channels/${channelId}`, { method: 'DELETE' })
      showSuccess('渠道已删除')
      loadChannels(selectedProject.id)
    } catch (e) { showError('删除失败: ' + e.message) }
  }

  const openEditChannel = (ch) => {
    setNewChannel({
      channel_type: ch.channel_type,
      report_format: ch.report_format || 'markdown',
      config: ch.config || {}
    })
    setEditingChannel(ch)
    setShowModal('editChannel')
  }

  const updateChannel = async () => {
    if (!selectedProject || !editingChannel) return
    try {
      await apiFetch(`/projects/${selectedProject.id}/channels/${editingChannel.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          channel_type: newChannel.channel_type,
          report_format: newChannel.report_format,
          config: newChannel.config,
          enabled: 1,
        })
      })
      closeChannelModal()
      setEditingChannel(null)
      showSuccess('渠道更新成功')
      loadChannels(selectedProject.id)
    } catch (e) { showError('更新失败: ' + e.message) }
  }

  const sendReportToChannel = async (channelId) => {
    if (!selectedProject) return
    const recordsResp = await apiFetch(`/projects/${selectedProject.id}/records`)
    if (!recordsResp.length) {
      showError('没有可发送的巡检记录')
      return
    }
    const latestId = recordsResp[0].id
    setLoading(true)
    try {
      const url = channelId ? `/records/${latestId}/send/${channelId}` : `/records/${latestId}/send`
      const data = await apiFetch(url, { method: 'POST' })
      const results = data.results || [data]
      const successCount = results.filter(r => r.status === 'success').length
      const failCount = results.filter(r => r.status === 'failed').length
      if (failCount > 0) {
        showSuccess(`发送完成: ${successCount} 成功, ${failCount} 失败`)
      } else {
        showSuccess(`报告已成功发送到 ${successCount} 个渠道`)
      }
      loadNotificationLogs(selectedProject.id)
    } catch (e) { showError('发送失败: ' + e.message) }
    setLoading(false)
  }

  const sendReport = async (recordId) => {
    if (!selectedProject) return
    setLoading(true)
    try {
      const data = await apiFetch(`/records/${recordId}/send`, { method: 'POST' })
      const results = data.results || [data]
      const successCount = results.filter(r => r.status === 'success').length
      const failCount = results.filter(r => r.status === 'failed').length
      if (failCount > 0) {
        showSuccess(`推送完成: ${successCount} 成功, ${failCount} 失败`)
      } else {
        showSuccess(`报告已推送到 ${successCount} 个渠道`)
      }
      loadNotificationLogs(selectedProject.id)
    } catch (e) { showError('推送失败: ' + e.message) }
    setLoading(false)
  }

  const toggleChannelEnabled = async (ch) => {
    if (!selectedProject) return
    const newEnabled = ch.enabled ? 0 : 1
    try {
      await apiFetch(`/projects/${selectedProject.id}/channels/${ch.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          channel_type: ch.channel_type,
          report_format: ch.report_format || 'markdown',
          config: ch.config || {},
          enabled: newEnabled
        })
      })
      showSuccess(newEnabled ? '渠道已启用' : '渠道已禁用')
      loadChannels(selectedProject.id)
    } catch (e) { showError('操作失败: ' + e.message) }  }

  // Records
  const loadRecords = async (projectId, filter) => {
    const tf = filter || recordFilter
    try {
      const url = `/projects/${projectId}/records` + (tf && tf !== 'all' ? `?trigger_type=${tf}` : '')
      const data = await apiFetch(url)
      setRecords(data)
    } catch (e) { /* ignore */ }
  }

  // Trigger inspection
  const triggerInspection = async () => {
    if (!selectedProject) return
    setLoading(true)
    try {
      const data = await apiFetch(`/projects/${selectedProject.id}/inspect`, { method: 'POST' })
      showSuccess(`巡检已触发 (记录ID: ${data.record_id})`)
      loadRecords(selectedProject.id)
      loadStats()
    } catch (e) { showError('触发巡检失败: ' + e.message) }
    setLoading(false)
  }

  // View report
  const viewReport = async (recordId) => {
    try {
      const data = await apiFetch(`/records/${recordId}/preview`)
      setReportData(data)
      setActiveTab('report')
    } catch (e) { showError('加载报告失败') }
  }

  // Delete record
  const deleteRecord = async (recordId) => {
    if (!confirm('确定要删除该巡检记录吗？此操作不可恢复。')) return
    try {
      await apiFetch(`/records/${recordId}`, { method: 'DELETE' })
      showSuccess('巡检记录已删除')
      if (selectedProject) loadRecords(selectedProject.id)
    } catch (e) { showError('删除失败: ' + e.message) }
  }

  // Create project
  const createProject = async () => {
    if (!newProject.name || !newProject.prometheus_url) {
      showError('请填写项目名称和Prometheus地址')
      return
    }
    try {
      await apiFetch('/projects', {
        method: 'POST',
        body: JSON.stringify(newProject)
      })
      setShowModal(null)
      setNewProject({ name: '', env: 'production', prometheus_url: '', auth_enabled: false, auth_username: '', auth_password: '', description: '' })
      showSuccess('项目创建成功')
      loadProjects()
      loadStats()
    } catch (e) { showError('创建项目失败: ' + e.message) }
  }

  // Edit project
  const openEditProject = (project, e) => {
    e.stopPropagation()
    setNewProject({
      name: project.name,
      env: project.env,
      prometheus_url: project.prometheus_url,
      auth_enabled: !!project.auth_enabled,
      auth_username: project.auth_username || '',
      auth_password: project.auth_password || '',
      description: project.description || ''
    })
    setEditingProject(project)
    setShowModal('editProject')
  }

  const updateProject = async () => {
    if (!newProject.name || !newProject.prometheus_url) {
      showError('请填写项目名称和Prometheus地址')
      return
    }
    try {
      await apiFetch(`/projects/${editingProject.id}`, {
        method: 'PUT',
        body: JSON.stringify(newProject)
      })
      setShowModal(null)
      setEditingProject(null)
      setNewProject({ name: '', env: 'production', prometheus_url: '', auth_enabled: false, auth_username: '', auth_password: '', description: '' })
      showSuccess('项目更新成功')
      loadProjects()
    } catch (e) { showError('更新项目失败: ' + e.message) }
  }

  // Delete project
  const deleteProject = async (projectId) => {
    if (!confirm('确定删除此项目？所有相关配置和数据将被删除。')) return
    try {
      await apiFetch(`/projects/${projectId}`, { method: 'DELETE' })
      if (selectedProject?.id === projectId) setSelectedProject(null)
      showSuccess('项目已删除')
      loadProjects()
      loadStats()
    } catch (e) { showError('删除失败') }
  }

  // Test notification
  const testChannel = async (channel) => {
    try {
      await apiFetch('/test/notification', {
        method: 'POST',
        body: JSON.stringify({
          project_id: selectedProject?.id,
          channel_id: channel.id,
          channel_type: channel.channel_type,
          config: channel.config
        })
      })
      showSuccess('测试消息发送成功')
      if (selectedProject) loadNotificationLogs(selectedProject.id)
    } catch (e) { showError('测试发送失败: ' + e.message) }
  }

  // Test Prometheus connection
  const testPrometheus = async () => {
    try {
      const data = await apiFetch('/test/prometheus', {
        method: 'POST',
        body: JSON.stringify({ url: newProject.prometheus_url, auth_enabled: newProject.auth_enabled, username: newProject.auth_username, password: newProject.auth_password })
      })
      if (data.status === 'success') {
        showSuccess(`连接成功！发现 ${data.target_count} 个Target`)
      }
    } catch (e) { showError('连接失败: ' + e.message) }
  }

  const [newDatasource, setNewDatasource] = useState({
    name: '', url: '', ds_type: 'prometheus', auth_enabled: false, auth_username: '', auth_password: ''
  })

  // Add datasource
  const saveDatasource = async () => {
    if (!selectedProject) return
    try {
      await apiFetch(`/projects/${selectedProject.id}/datasources`, {
        method: 'POST',
        body: JSON.stringify(newDatasource)
      })
      showSuccess('数据源创建成功')
      setShowModal(null)
      setNewDatasource({ name: '', url: '', ds_type: 'prometheus', auth_enabled: false, auth_username: '', auth_password: '' })
      loadDatasources(selectedProject.id)
    } catch (e) { showError('创建失败: ' + e.message) }
  }

  const deleteDatasource = async (dsId) => {
    if (!selectedProject) return
    if (!confirm('确定删除此数据源？')) return
    try {
      await apiFetch(`/projects/${selectedProject.id}/datasources/${dsId}`, {
        method: 'DELETE'
      })
      showSuccess('数据源已删除')
      loadDatasources(selectedProject.id)
    } catch (e) { showError('删除失败: ' + e.message) }
  }

  const testDatasource = async (dsId) => {
    if (!selectedProject) return
    try {
      const data = await apiFetch(`/projects/${selectedProject.id}/datasources/${dsId}/test`, {
        method: 'POST'
      })
      if (data.status === 'success') {
        showSuccess('连接成功！')
      } else {
        showError('连接失败: ' + (data.message || data.error || '未知错误'))
      }
    } catch (e) { showError('测试失败: ' + e.message) }
  }

  // Add plugin
  const addPlugin = (pluginName) => {
    const pluginInfo = AVAILABLE_PLUGINS.find(p => p.name === pluginName)
    setPluginConfigs([...pluginConfigs, {
      plugin_name: pluginName,
      enabled: true,
      job_pattern: pluginInfo?.defaultPattern || pluginName,
      thresholds: {},
      extra_config: {},
    }])
    setShowModal(null)
  }

  const tabs = [
    { id: 'projects', label: '项目管理', icon: Server },
    { id: 'plugins', label: '插件配置', icon: Layers },
    { id: 'datasources', label: '数据源', icon: Database },
    { id: 'channels', label: '通知渠道', icon: Bell },
    { id: 'notification-logs', label: '推送日志', icon: MessageSquare },
    { id: 'schedules', label: '定时任务', icon: Clock },
    { id: 'records', label: '巡检记录', icon: FileText },
    { id: 'report', label: '报告预览', icon: Eye },
    { id: 'settings', label: '系统设置', icon: Settings },
  ]

  // === RENDERERS ===

  const renderProjects = () => (
    <div className="animate-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">项目列表</h2>
          <p className="text-sm text-slate-500 mt-0.5">管理所有被巡检的 Prometheus 项目</p>
        </div>
        <button onClick={() => setShowModal('addProject')}
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/20">
          <Plus size={16} /> 新增项目
        </button>
      </div>
      {projects.length === 0 ? (
        <div className="bg-white rounded-2xl p-16 text-center border border-slate-200 card-hover">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Database size={32} className="text-slate-300" />
          </div>
          <p className="text-lg font-medium text-slate-500">暂无项目</p>
          <p className="text-sm text-slate-400 mt-1.5">点击上方「新增项目」添加您的第一个监控项目</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {projects.map((p, i) => (
            <div key={p.id}
              className={`bg-white rounded-2xl p-6 card-hover border-2 cursor-pointer ${selectedProject?.id === p.id ? 'border-indigo-500 shadow-lg shadow-indigo-500/10' : 'border-slate-200 hover:border-slate-300'}`}
              onClick={() => selectProject(p)}
              style={{ animationDelay: `${i * 50}ms` }}>
              <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-lg text-slate-800">{p.name}</h3>
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${p.env === 'production' ? 'bg-rose-50 text-rose-600 border border-rose-200' : 'bg-amber-50 text-amber-600 border border-amber-200'}`}>
                      {p.env}
                    </span>
                    {p.auth_enabled ? (
                      <span className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-amber-50 text-amber-600 border border-amber-200">
                        <Shield size={12} /> Auth
                      </span>
                    ) : null}
                  </div>
                  {p.description && (
                    <p className="text-sm text-slate-500 mt-1.5">{p.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-3">
                    <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
                      <Server size={12} className="text-slate-400" />
                      {p.prometheus_url}
                    </div>
                  </div>
                </div>
                <div className="flex gap-1.5 items-start ml-4 shrink-0">
                  <button onClick={(e) => openEditProject(p, e)}
                    className="text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 p-2 rounded-xl transition" title="编辑">
                    <Edit3 size={16} />
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); selectProject(p); triggerInspection() }}
                    className="text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 p-2 rounded-xl transition" title="触发巡检">
                    <Play size={16} />
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); deleteProject(p.id) }}
                    className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 p-2 rounded-xl transition" title="删除">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const renderGenericSection = (config, idx) => {
    if (config.plugin_name !== 'generic') return null
    const queries = config.extra_config?.queries || []
    return (
      <div className="mt-4 border-t pt-4">
        <div className="flex items-center justify-between mb-3">
          <label className="text-sm font-medium text-slate-600">自定义指标查询</label>
          <button onClick={() => { setMetricEditorIdx(idx); setShowModal('editMetrics') }}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1">
            <Edit3 size={14} /> 编辑查询
          </button>
        </div>
        <div className="space-y-2">
          {queries.length === 0 ? (
            <span className="text-xs text-slate-400">尚未配置查询，点击"编辑查询"添加</span>
          ) : (
            queries.slice(0, 3).map((q, qi) => (
              <div key={qi} className="flex items-center gap-2 text-xs bg-slate-50 rounded-lg px-3 py-2">
                <span className="font-medium text-slate-700 w-24 truncate">{q.name}</span>
                <span className="text-slate-400 truncate flex-1">{q.promql}</span>
                <span className={'px-2 py-0.5 rounded-full ' + (q.severity === 'critical' ? 'text-rose-600 bg-rose-50' : 'text-amber-600 bg-amber-50')}>
                  {q.threshold || '-'}
                </span>
              </div>
            ))
          )}
          {queries.length > 3 && (
            <span className="text-xs text-slate-400">...还有 {queries.length - 3} 个查询</span>
          )}
        </div>
      </div>
    )
  }

  const renderPlugins = () => (
    <div className="animate-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">插件配置</h2>
          {selectedProject && (
            <p className="text-sm text-slate-500 mt-0.5">
              项目: <span className="font-semibold text-indigo-600">{selectedProject.name}</span>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button onClick={handleDiscover} disabled={loading}
            className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2.5 rounded-xl hover:bg-emerald-700 transition disabled:opacity-50 shadow-sm font-medium text-sm">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 自动发现
          </button>
          <button onClick={savePlugins}
            className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2.5 rounded-xl hover:bg-indigo-700 transition shadow-sm font-medium text-sm">
            <Settings size={16} /> 保存配置
          </button>
        </div>
      </div>

      {!selectedProject && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-amber-700 text-sm flex items-center gap-3">
          <AlertTriangle size={18} className="shrink-0" />
          <span>请先在「项目管理」中选择一个项目</span>
        </div>
      )}

      {discoveredJobs && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 mb-6">
          <h4 className="font-semibold text-emerald-800 mb-3 flex items-center gap-2">
            <CheckCircle size={16} /> 已发现的 Job
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(discoveredJobs).map(([job, info]) => (
              <div key={job} className="bg-white rounded px-3 py-2 text-sm border">
                <span className="font-mono font-medium">{job}</span>
                <div className="flex gap-2 mt-1 text-xs">
                  <span className="text-green-600">↑{info.up}</span>
                  {info.down > 0 && <span className="text-red-500">↓{info.down}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {pluginConfigs.map((config, idx) => {
          const pluginInfo = AVAILABLE_PLUGINS.find(p => p.name === config.plugin_name)
          return (
            <div key={idx} className={`bg-white border-2 rounded-2xl p-5 card-hover ${config.enabled ? 'border-slate-200' : 'border-slate-100 opacity-60'}`}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" checked={config.enabled}
                        onChange={() => {
                          const updated = [...pluginConfigs]
                          updated[idx] = { ...updated[idx], enabled: !updated[idx].enabled }
                          setPluginConfigs(updated)
                        }}
                        className="sr-only peer" />
                      <div className="w-10 h-5 bg-slate-200 rounded-full peer peer-checked:bg-indigo-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[3px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all"></div>
                    </label>
                    <h3 className="font-semibold text-slate-800">{pluginInfo?.label || config.plugin_name}</h3>
                    <span className="text-xs text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full">{pluginInfo?.description}</span>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-4 items-end">
                    <div>
                      <label className="text-xs font-medium text-slate-500 block mb-1.5">Job 匹配模式（正则）</label>
                      <input type="text" value={config.job_pattern}
                        onChange={(e) => {
                          const updated = [...pluginConfigs]
                          updated[idx] = { ...updated[idx], job_pattern: e.target.value }
                          setPluginConfigs(updated)
                        }}
                        className="border border-slate-200 rounded-xl px-3 py-2 text-sm font-mono w-56 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none bg-slate-50" />
                    </div>
                    {Object.entries(config.thresholds || {}).map(([key, val]) => (
                      <div key={key}>
                        <label className="text-xs font-medium text-slate-500 block mb-1.5">{key}</label>
                        <input type="number" value={val}
                          onChange={(e) => {
                            const updated = [...pluginConfigs]
                            updated[idx] = { ...updated[idx], thresholds: { ...updated[idx].thresholds, [key]: Number(e.target.value) } }
                            setPluginConfigs(updated)
                          }}
                          className="border border-slate-200 rounded-xl px-3 py-2 text-sm w-24 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none bg-slate-50" />
                      </div>))}
                    {Object.keys(config.thresholds || {}).length === 0 && (
                      <span className="text-xs text-slate-400 pb-2">无阈值配置</span>
                    )}
                  </div>
                  {datasources.length > 0 && (
                    <div className="mt-3 flex items-center gap-4">
                      <div>
                        <label className="text-xs font-medium text-slate-500 block mb-1">数据源</label>
                        <select value={config.datasource_id || ''}
                          onChange={(e) => {
                            const updated = [...pluginConfigs]
                            updated[idx] = { ...updated[idx], datasource_id: e.target.value ? Number(e.target.value) : null }
                            setPluginConfigs(updated)
                          }}
                          className="border border-slate-200 rounded-lg px-2 py-1.5 text-xs focus:border-indigo-400 outline-none bg-white">
                          <option value="">默认（项目配置）</option>
                          {datasources.map(ds => (
                            <option key={ds.id} value={ds.id}>{ds.name}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-slate-500 block mb-1">实例过滤（可选）</label>
                        <input type="text" value={config.filter_config?.whitelist?.[0] || ''}
                          onChange={(e) => {
                            const updated = [...pluginConfigs]
                            const fc = { ...(updated[idx].filter_config || {}), whitelist: e.target.value ? [e.target.value] : [] }
                            updated[idx] = { ...updated[idx], filter_config: fc }
                            setPluginConfigs(updated)
                          }}
                          className="border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-mono focus:border-indigo-400 outline-none bg-slate-50 w-48"
                          placeholder="正则匹配，如: :9100$" />
                      </div>
                    </div>
                  )}
                  {renderGenericSection(config, idx)}
                </div>
                <button className="text-slate-400 hover:text-rose-600 p-2 rounded-xl hover:bg-rose-50 transition"
                  onClick={() => setPluginConfigs(pluginConfigs.filter((_, i) => i !== idx))}>
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          )
        })}
      </div>
      <button onClick={() => setShowModal('addPlugin')}
        className="mt-4 w-full border-2 border-dashed border-slate-300 rounded-2xl py-4 text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition flex items-center justify-center gap-2 font-medium">
        <Plus size={16} /> 添加巡检插件
      </button>
    </div>
  )

  const renderChannels = () => (
    <div className="animate-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">通知渠道</h2>
          {selectedProject && (
            <p className="text-sm text-slate-500 mt-0.5">
              项目: <span className="font-semibold text-indigo-600">{selectedProject.name}</span>
            </p>
          )}
        </div>
        {(channels.length < 2) && (
          <button onClick={openAddChannel}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/20 font-medium text-sm">
            <Plus size={16} /> 添加渠道
          </button>
        )}
      </div>

      {!selectedProject && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-amber-700 text-sm flex items-center gap-3">
          <AlertTriangle size={18} className="shrink-0" />
          <span>请先在「项目管理」中选择一个项目</span>
        </div>
      )}

      {channels.length === 0 && selectedProject && (
        <div className="bg-white rounded-2xl p-16 text-center border border-slate-200 card-hover">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Bell size={32} className="text-slate-300" />
          </div>
          <p className="text-lg font-medium text-slate-500">暂无通知渠道</p>
          <p className="text-sm text-slate-400 mt-1.5">点击上方「添加渠道」配置通知方式</p>
        </div>
      )}

      <div className="space-y-3">
        {channels.map(ch => (
          <div key={ch.id} className={`bg-white border-2 rounded-2xl p-5 card-hover ${ch.enabled ? 'border-slate-200' : 'border-slate-100 opacity-60'}`}>
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-4">
                <div className={`w-11 h-11 rounded-2xl flex items-center justify-center ${ch.channel_type === 'feishu' ? 'bg-blue-50 text-blue-600' : 'bg-emerald-50 text-emerald-600'}`}>
                  {ch.channel_type === 'feishu' ? <MessageSquare size={20} /> : <Mail size={20} />}
                </div>
                <div>
                  <h3 className={`font-semibold ${ch.enabled ? 'text-slate-800' : 'text-slate-400'}`}>
                    {ch.channel_type === 'feishu' ? '飞书机器人' : '邮件通知'}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 font-mono max-w-md truncate">
                    {ch.channel_type === 'feishu'
                      ? ch.config?.webhook_url || ''
                      : ch.config?.smtp_host || ''}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={!!ch.enabled}
                    onChange={() => toggleChannelEnabled(ch)} />
                  <div className="w-9 h-5 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
                <span className={`text-xs font-medium ${ch.enabled ? 'text-indigo-600' : 'text-slate-400'}`}>{ch.enabled ? '已启用' : '已禁用'}</span>
                <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg">{ch.report_format}</span>
                <button onClick={() => sendReportToChannel(ch.id)}
                  className={`p-2 rounded-xl transition ${ch.enabled ? 'text-slate-400 hover:text-indigo-600 hover:bg-indigo-50' : 'text-slate-300 cursor-not-allowed'}`} title="发送报告" disabled={!ch.enabled}>
                  <Play size={16} />
                </button>
                <button onClick={() => openEditChannel(ch)}
                  className="text-slate-400 hover:text-slate-600 hover:bg-slate-100 p-2 rounded-xl transition" title="编辑">
                  <Edit3 size={16} />
                </button>
                <button onClick={() => testChannel(ch)}
                  className="text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 p-2 rounded-xl transition" title="测试发送">
                  <TestTube size={16} />
                </button>
                <button onClick={() => deleteChannel(ch.id)}
                  className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 p-2 rounded-xl transition" title="删除">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-white rounded-2xl p-6 border border-slate-200">
        <h3 className="font-semibold text-slate-700 mb-4">各渠道支持的报告格式</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-100">
                <th className="pb-3 pr-6 font-medium">渠道</th>
                <th className="pb-3 pr-6 font-medium">Markdown</th>
                <th className="pb-3 pr-6 font-medium">HTML</th>
                <th className="pb-3 font-medium">纯文本</th>
              </tr>
            </thead>
            <tbody className="text-slate-600">
              <tr className="border-b border-slate-50"><td className="py-3 pr-6 font-medium">飞书</td><td className="py-3 pr-6">推荐</td><td className="py-3 pr-6">卡片消息</td><td className="py-3">支持</td></tr>
              <tr><td className="py-3 pr-6 font-medium">邮件</td><td className="py-3 pr-6">支持</td><td className="py-3 pr-6">推荐</td><td className="py-3">支持</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )

  const renderDatasources = () => (
    <div className="animate-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">数据源管理</h2>
          {selectedProject && (
            <p className="text-sm text-slate-500 mt-0.5">
              项目: <span className="font-semibold text-indigo-600">{selectedProject.name}</span>
            </p>
          )}
        </div>
        <button onClick={() => setShowModal('addDatasource')}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2.5 rounded-xl hover:bg-indigo-700 transition shadow-sm font-medium text-sm">
          <Plus size={16} /> 添加数据源
        </button>
      </div>

      {!selectedProject && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-amber-700 text-sm flex items-center gap-3">
          <AlertTriangle size={18} className="shrink-0" />
          <span>请先在「项目管理」中选择一个项目</span>
        </div>
      )}

      {datasources.length === 0 && selectedProject && (
        <div className="bg-white rounded-2xl p-16 text-center border border-slate-200 card-hover">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Database size={32} className="text-slate-300" />
          </div>
          <p className="text-lg font-medium text-slate-500">暂无数据源</p>
          <p className="text-sm text-slate-400 mt-1.5">点击上方「添加数据源」配置 Prometheus 或其他监控数据源</p>
          <p className="text-xs text-slate-400 mt-1">默认使用项目的 Prometheus 地址作为主数据源</p>
        </div>
      )}

      {selectedProject && datasources.length > 0 && (
        <div className="space-y-3">
          {datasources.map((ds) => (
            <div key={ds.id} className="bg-white border border-slate-200 rounded-2xl p-5 card-hover">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-slate-800">{ds.name}</h3>
                  <p className="text-sm text-slate-500 mt-1 font-mono">{ds.url}</p>
                  <div className="flex gap-4 mt-2 text-xs text-slate-400">
                    <span>类型: {ds.ds_type}</span>
                    <span>认证: {ds.auth_enabled ? '已启用' : '未启用'}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => testDatasource(ds.id)}
                    className="text-xs text-indigo-600 hover:bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-200 transition flex items-center gap-1">
                    <TestTube size={14} /> 测试
                  </button>
                  <button onClick={() => deleteDatasource(ds.id)}
                    className="text-xs text-rose-600 hover:bg-rose-50 px-3 py-1.5 rounded-lg border border-rose-200 transition flex items-center gap-1">
                    <Trash2 size={14} /> 删除
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const renderNotificationLogs = () => (
    <div className="animate-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">推送日志</h2>
          {selectedProject && (
            <p className="text-sm text-slate-500 mt-0.5">
              项目: <span className="font-semibold text-indigo-600">{selectedProject.name}</span>
            </p>
          )}
        </div>
      </div>

      {!selectedProject && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-amber-700 text-sm flex items-center gap-3">
          <AlertTriangle size={18} className="shrink-0" />
          <span>请先在「项目管理」中选择一个项目</span>
        </div>
      )}

      {notificationLogs.length === 0 && selectedProject && (
        <div className="bg-white rounded-2xl p-16 text-center border border-slate-200 card-hover">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <MessageSquare size={32} className="text-slate-300" />
          </div>
          <p className="text-lg font-medium text-slate-500">暂无推送日志</p>
          <p className="text-sm text-slate-400 mt-1.5">推送通知后将自动记录</p>
        </div>
      )}

      {notificationLogs.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">时间</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">渠道</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">状态</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">错误信息</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">操作</th>
              </tr>
            </thead>
            <tbody>
              {notificationLogs.map(log => (
                <tr key={log.id} className="border-t border-slate-100 table-row-hover transition">
                  <td className="px-5 py-3.5 font-mono text-slate-600 text-xs">{log.created_at?.replace('T', ' ') || '-'}</td>
                  <td className="px-5 py-3.5">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-slate-600">{log.channel_type}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    {log.status === 'success' ? (
                      <CheckCircle size={18} className="text-emerald-500" />
                    ) : (
                      <XCircle size={18} className="text-rose-500" />
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-xs text-slate-500 max-w-xs truncate">{log.error || '-'}</td>
                  <td className="px-5 py-3.5">
                    <button onClick={() => deleteNotificationLog(log.id)}
                      className="text-rose-600 hover:bg-rose-50 px-2 py-1 rounded-lg text-xs transition">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )

  const renderSchedules = () => (
    <div className="animate-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">定时任务</h2>
          {selectedProject && (
            <p className="text-sm text-slate-500 mt-0.5">
              项目: <span className="font-semibold text-indigo-600">{selectedProject.name}</span>
            </p>
          )}
        </div>
        <button onClick={() => { setEditingSchedule({ cron_expression: '0 9 * * *', enabled: 1, description: '' }); setShowModal('addSchedule') }}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2.5 rounded-xl hover:bg-indigo-700 transition shadow-sm font-medium text-sm">
          <Plus size={16} /> 添加任务
        </button>
      </div>

      {!selectedProject && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-amber-700 text-sm flex items-center gap-3">
          <AlertTriangle size={18} className="shrink-0" />
          <span>请先在「项目管理」中选择一个项目</span>
        </div>
      )}

      {schedules.length === 0 && selectedProject && (
        <div className="bg-white rounded-2xl p-16 text-center border border-slate-200 card-hover">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Clock size={32} className="text-slate-300" />
          </div>
          <p className="text-lg font-medium text-slate-500">暂无定时任务</p>
          <p className="text-sm text-slate-400 mt-1.5">添加定时任务自动执行巡检</p>
        </div>
      )}

      {schedules.length > 0 && (
        <div className="space-y-3">
          {schedules.map(s => (
            <div key={s.id} className="bg-white border border-slate-200 rounded-2xl p-5 card-hover">
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-4">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" checked={s.enabled}
                      onChange={() => toggleSchedule(s)}
                      className="sr-only peer" />
                    <div className="w-10 h-5 bg-slate-200 rounded-full peer peer-checked:bg-indigo-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[3px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all"></div>
                  </label>
                  <div>
                    <h3 className="font-semibold text-slate-800">
                      <span className="font-mono bg-slate-100 px-2 py-0.5 rounded text-sm">{s.cron_expression}</span>
                    </h3>
                    <p className="text-sm text-slate-500 mt-0.5">{s.description || '无描述'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => { setEditingSchedule({ ...s }); setShowModal('addSchedule') }}
                    className="text-slate-400 hover:text-indigo-600 p-2 rounded-xl hover:bg-indigo-50 transition">
                    <Edit3 size={16} />
                  </button>
                  <button onClick={() => deleteSchedule(s.id)}
                    className="text-rose-400 hover:text-rose-600 p-2 rounded-xl hover:bg-rose-50 transition">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const renderScheduleModal = () => (
    <div className="fixed inset-0 modal-backdrop flex items-center justify-center z-50" onClick={() => setShowModal(null)}>
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-2xl animate-slide-up" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-slate-800 mb-4">{editingSchedule?.id ? '编辑定时任务' : '添加定时任务'}</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Cron 表达式</label>
            <input type="text" value={editingSchedule?.cron_expression || ''}
              onChange={e => setEditingSchedule({ ...editingSchedule, cron_expression: e.target.value })}
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:border-indigo-400 outline-none" />
            <p className="text-xs text-slate-400 mt-1">格式: 分 时 日 月 周 (例如 0 9 * * * 表示每天9点)</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">描述</label>
            <input type="text" value={editingSchedule?.description || ''}
              onChange={e => setEditingSchedule({ ...editingSchedule, description: e.target.value })}
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:border-indigo-400 outline-none"
              placeholder="例如: 每日上午9点巡检" />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={() => setShowModal(null)}
            className="px-5 py-2.5 text-sm font-medium text-slate-600 bg-slate-100 rounded-xl hover:bg-slate-200 transition">取消</button>
          <button onClick={saveSchedule}
            className="px-5 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 transition shadow-sm">保存</button>
        </div>
      </div>
    </div>
  )

  const renderRecords = () => (
    <div className="animate-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">巡检记录</h2>
          {selectedProject && (
            <p className="text-sm text-slate-500 mt-0.5">
              项目: <span className="font-semibold text-indigo-600">{selectedProject.name}</span>
            </p>
          )}
        </div>
        <button onClick={triggerInspection} disabled={loading || !selectedProject}
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl hover:bg-indigo-700 transition disabled:opacity-50 shadow-lg shadow-indigo-500/20 font-medium text-sm">
          <Play size={16} className={loading ? 'animate-pulse' : ''} /> {loading ? '执行中...' : '立即巡检'}
        </button>
      </div>

      {!selectedProject && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-amber-700 text-sm flex items-center gap-3">
          <AlertTriangle size={18} className="shrink-0" />
          <span>请先在「项目管理」中选择一个项目</span>
        </div>
      )}

      {selectedProject && (
        <div className="flex items-center gap-3 mb-4">
          <select value={recordFilter}
            onChange={(e) => { setRecordFilter(e.target.value); loadRecords(selectedProject.id, e.target.value) }}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-400 outline-none bg-white">
            <option value="all">全部记录</option>
            <option value="manual">手动触发</option>
            <option value="scheduled">定时触发</option>
          </select>
          <span className="text-xs text-slate-400">共 {records.length} 条</span>
        </div>
      )}

      {records.length === 0 && selectedProject && (
        <div className="bg-white rounded-2xl p-16 text-center border border-slate-200 card-hover">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <FileText size={32} className="text-slate-300" />
          </div>
          <p className="text-lg font-medium text-slate-500">暂无巡检记录</p>
          <p className="text-sm text-slate-400 mt-1.5">点击上方「立即巡检」开始第一次巡检</p>
        </div>
      )}

      {records.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">时间</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">触发方式</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">状态</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">巡检项</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">异常</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600">操作</th>
              </tr>
            </thead>
            <tbody>
              {records.map(r => (
                <tr key={r.id} className="border-t border-slate-100 table-row-hover transition">
                  <td className="px-5 py-3.5 font-mono text-slate-600 text-xs">{r.started_at?.replace('T', ' ') || '-'}</td>
                  <td className="px-5 py-3.5">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${r.trigger_type === 'scheduled' ? 'bg-blue-50 text-blue-600 border border-blue-200' : 'bg-purple-50 text-purple-600 border border-purple-200'}`}>
                      {r.trigger_type === 'scheduled' ? '定时' : '手动'}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    {r.status === 'success' ? <CheckCircle size={18} className="text-emerald-500" /> :
                     r.status === 'failed' ? <XCircle size={18} className="text-rose-500" /> :
                     <RefreshCw size={18} className="text-amber-500 animate-spin" />}
                  </td>
                  <td className="px-5 py-3.5 text-slate-600">{r.total_items}</td>
                  <td className="px-5 py-3.5">
                    {r.abnormal_items > 0 ? (
                      <span className="text-rose-600 font-semibold bg-rose-50 px-2.5 py-1 rounded-lg">{r.abnormal_items}</span>
                    ) : (
                      <span className="text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-lg">0</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                    <button onClick={() => viewReport(r.id)}
                      className="text-indigo-600 hover:bg-indigo-50 px-3 py-1.5 rounded-xl text-sm font-medium transition flex items-center gap-1.5">
                      <Eye size={14} /> 报告
                    </button>
                    {r.status === 'success' && (
                      <button onClick={() => sendReport(r.id)}
                        className="text-emerald-600 hover:bg-emerald-50 px-3 py-1.5 rounded-xl text-sm font-medium transition flex items-center gap-1.5">
                        <Bell size={14} /> 推送
                      </button>
                    )}
                    <button onClick={() => deleteRecord(r.id)}
                      className="text-rose-600 hover:bg-rose-50 px-3 py-1.5 rounded-xl text-sm font-medium transition flex items-center gap-1.5">
                      <Trash2 size={14} /> 删除
                    </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )

  const renderReport = () => {
    const content = reportFormat === 'html' ? reportData.html :
                    reportFormat === 'markdown' ? reportData.markdown :
                    reportFormat === 'json' ? JSON.stringify(reportData.summary || {}, null, 2) :
                    reportData.markdown

    return (
      <div className="animate-slide-up">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-800">报告预览</h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex bg-slate-100 rounded-xl p-1 gap-0.5">
              {REPORT_FORMATS.map(f => (
                <button key={f.value} onClick={() => setReportFormat(f.value)}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-all duration-150 ${reportFormat === f.value ? 'bg-white shadow-sm font-medium text-indigo-700' : 'text-slate-500 hover:text-slate-700'}`}>
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {!reportData.html && !reportData.markdown ? (
          <div className="bg-white rounded-2xl p-16 text-center border border-slate-200 card-hover">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Eye size={32} className="text-slate-300" />
            </div>
            <p className="text-lg font-medium text-slate-500">暂无报告内容</p>
            <p className="text-sm text-slate-400 mt-1.5">请先执行巡检并选择一条记录查看报告</p>
          </div>
        ) : reportFormat === 'html' ? (
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm"
            dangerouslySetInnerHTML={{ __html: content }} />
        ) : reportFormat === 'json' ? (
          <div className="bg-slate-900 rounded-2xl p-6 text-slate-100 font-mono text-sm whitespace-pre-wrap overflow-x-auto max-h-[70vh] overflow-y-auto shadow-sm border border-slate-700">
            {content}
          </div>
        ) : (
          <div className="bg-slate-900 rounded-2xl p-6 text-slate-100 font-mono text-sm whitespace-pre-wrap overflow-x-auto max-h-[70vh] overflow-y-auto shadow-sm border border-slate-700">
            {content}
          </div>
        )}
      </div>
    )
  }

  const renderSettings = () => (
    <div className="animate-slide-up">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">系统设置</h2>
          <p className="text-sm text-slate-500 mt-0.5">配置数据保留策略等全局参数</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-6 border border-slate-200 max-w-2xl">
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">巡检记录保留天数</label>
            <input type="number" min="1" max="365" value={settings.records_retention_days}
              onChange={e => setSettings({ ...settings, records_retention_days: e.target.value })}
              className="w-40 px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 outline-none" />
            <p className="text-xs text-slate-400 mt-1">超过此天数的巡检记录和详情将被自动清理</p>
          </div>

          <button onClick={async () => {
            setSavingSettings(true)
            try {
              await apiFetch('/settings', {
                method: 'PUT',
                body: JSON.stringify(settings)
              })
              showSuccess('设置已保存')
            } catch (e) { showError('保存失败: ' + e.message) }
            setSavingSettings(false)
          }} disabled={savingSettings}
            className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/20 text-sm font-medium disabled:opacity-50">
            <Settings size={16} /> {savingSettings ? '保存中...' : '保存设置'}
          </button>
        </div>
      </div>
    </div>
  )

  const closeProjectModal = () => {
    setShowModal(null)
    setEditingProject(null)
    setNewProject({ name: '', env: 'production', prometheus_url: '', auth_enabled: false, auth_username: '', auth_password: '', description: '' })
  }

  const renderAddProjectModal = () => {
    const isEdit = !!editingProject
    return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={closeProjectModal}>
      <div className="bg-white rounded-xl w-full max-w-lg p-6" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-bold mb-4">{isEdit ? '编辑项目' : '新增项目'}</h3>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-600 block mb-1">项目名称 *</label>
            <input type="text" value={newProject.name}
              onChange={e => setNewProject({ ...newProject, name: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none" placeholder="例: 智慧城市项目" />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-sm text-gray-600 block mb-1">环境</label>
              <select value={newProject.env}
                onChange={e => setNewProject({ ...newProject, env: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 focus:border-indigo-500 outline-none">
                <option value="production">production</option>
                <option value="staging">staging</option>
                <option value="testing">testing</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="text-sm text-gray-600 block mb-1">Prometheus地址 *</label>
              <input type="text" value={newProject.prometheus_url}
                onChange={e => setNewProject({ ...newProject, prometheus_url: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none" placeholder="http://10.0.0.1:9090" />
            </div>
          </div>
          <div>
            <label className="text-sm text-gray-600 block mb-1">描述</label>
            <input type="text" value={newProject.description}
              onChange={e => setNewProject({ ...newProject, description: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none" placeholder="项目描述" />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="authEnabled" checked={newProject.auth_enabled}
              onChange={e => setNewProject({ ...newProject, auth_enabled: e.target.checked })}
              className="rounded" />
            <label htmlFor="authEnabled" className="text-sm text-gray-600">启用Basic Auth认证</label>
          </div>
          {newProject.auth_enabled && (
            <div className="flex gap-3">
              <input type="text" value={newProject.auth_username}
                onChange={e => setNewProject({ ...newProject, auth_username: e.target.value })}
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:border-indigo-500 outline-none" placeholder="用户名" />
              <input type="password" value={newProject.auth_password}
                onChange={e => setNewProject({ ...newProject, auth_password: e.target.value })}
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:border-indigo-500 outline-none" placeholder="密码" />
            </div>
          )}
          <div className="flex gap-2">
            <button onClick={testPrometheus}
              className="flex-1 py-2 border rounded-lg text-gray-600 hover:bg-gray-50 text-sm">
              测试连接
            </button>
            <button onClick={isEdit ? updateProject : createProject}
              className="flex-1 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
              {isEdit ? '保存修改' : '创建项目'}
            </button>
          </div>
        </div>
        <button onClick={closeProjectModal} className="mt-3 w-full py-2 border rounded-lg text-gray-600 hover:bg-gray-50 text-sm">
          取消
        </button>
      </div>
    </div>
    )
  }

  const renderAddPluginModal = () => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={() => setShowModal(null)}>
      <div className="bg-white rounded-xl w-full max-w-lg max-h-96 overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-bold mb-4">选择要添加的巡检插件</h3>
        <div className="space-y-2">
          {AVAILABLE_PLUGINS.filter(p => !pluginConfigs.find(c => c.plugin_name === p.name)).map(plugin => (
            <button key={plugin.name} onClick={() => addPlugin(plugin.name)}
              className="w-full text-left p-3 border rounded-lg hover:border-indigo-400 hover:bg-indigo-50 transition flex justify-between items-center">
              <div>
                <span className="font-medium text-gray-800">{plugin.label}</span>
                <span className="text-xs text-gray-500 ml-2">{plugin.description}</span>
              </div>
              <ChevronRight size={16} className="text-gray-400" />
            </button>
          ))}
          {AVAILABLE_PLUGINS.filter(p => !pluginConfigs.find(c => c.plugin_name === p.name)).length === 0 && (
            <p className="text-gray-400 text-center py-4">所有插件已添加</p>
          )}
        </div>
        <button onClick={() => setShowModal(null)} className="mt-4 w-full py-2 border rounded-lg text-gray-600 hover:bg-gray-50">
          取消
        </button>
      </div>
    </div>
  )

  const renderAddChannelModal = () => {
    const isEdit = !!editingChannel
    const channelTypes = [
      { value: 'feishu', label: '飞书机器人', fields: [{ key: 'webhook_url', label: 'Webhook地址', placeholder: 'https://open.feishu.cn/open-apis/bot/v2/hook/...' }] },
      { value: 'email', label: '邮件通知', fields: [
        { key: 'smtp_host', label: 'SMTP主机', placeholder: 'smtp.company.com' },
        { key: 'smtp_port', label: '端口', placeholder: '465' },
        { key: 'username', label: '用户名', placeholder: 'user@company.com' },
        { key: 'password', label: '密码', placeholder: '********' },
        { key: 'to', label: '收件人(逗号分隔)', placeholder: 'ops@company.com' },
      ]},
    ]
    const ct = channelTypes.find(t => t.value === newChannel.channel_type) || channelTypes[0]

    const handleSave = async () => {
      if (!selectedProject) return
      // Validate required config fields
      const requiredFields = ct.fields.map(f => f.key)
      const emptyFields = requiredFields.filter(k => !String(newChannel.config[k] ?? '').trim())
      if (emptyFields.length) {
        showError(`请填写必填字段: ${emptyFields.join(', ')}`)
        return
      }
      try {
        if (isEdit) {
          await updateChannel()
        } else {
          await apiFetch(`/projects/${selectedProject.id}/channels`, {
            method: 'POST',
            body: JSON.stringify({
              channel_type: newChannel.channel_type,
              report_format: newChannel.report_format,
              config: newChannel.config,
              enabled: 1,
            })
          })
          closeChannelModal()
          showSuccess('渠道添加成功')
          loadChannels(selectedProject.id)
        }
      } catch (e) { showError('操作失败: ' + e.message) }
    }

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        onClick={closeChannelModal}>
        <div className="bg-white rounded-xl w-full max-w-lg p-6" onClick={e => e.stopPropagation()}>
          <h3 className="text-lg font-bold mb-4">{isEdit ? '编辑通知渠道' : '添加通知渠道'}</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-600 block mb-1">渠道类型</label>
              <select value={newChannel.channel_type}
                onChange={e => setNewChannel({ ...newChannel, channel_type: e.target.value, config: {} })}
                className="w-full border rounded-lg px-3 py-2 focus:border-indigo-500 outline-none">
                {channelTypes.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-600 block mb-1">报告格式</label>
              <select value={newChannel.report_format}
                onChange={e => setNewChannel({ ...newChannel, report_format: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 focus:border-indigo-500 outline-none">
                {REPORT_FORMATS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
            </div>
            {ct.fields.map(field => (
              <div key={field.key}>
                <label className="text-sm text-gray-600 block mb-1">{field.label}</label>
                <input type={field.key === 'password' ? 'password' : 'text'} value={newChannel.config[field.key] || ''}
                  onChange={e => setNewChannel({ ...newChannel, config: { ...newChannel.config, [field.key]: e.target.value } })}
                  className="w-full border rounded-lg px-3 py-2 focus:border-indigo-500 outline-none"
                  placeholder={field.placeholder} />
              </div>
            ))}
            <button onClick={handleSave}
              className="w-full py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
              {isEdit ? '保存修改' : '保存'}
            </button>
          </div>
          <button onClick={closeChannelModal} className="mt-3 w-full py-2 border rounded-lg text-gray-600 hover:bg-gray-50 text-sm">
            取消
          </button>
        </div>
      </div>
    )
  }

  const renderAddDatasourceModal = () => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={() => setShowModal(null)}>
      <div className="bg-white rounded-xl w-full max-w-lg p-6" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-bold mb-4">添加数据源</h3>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-600 block mb-1">名称</label>
            <input type="text" value={newDatasource.name}
              onChange={e => setNewDatasource({ ...newDatasource, name: e.target.value })}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-400 outline-none"
              placeholder="如: 生产环境 Prometheus" />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600 block mb-1">类型</label>
            <select value={newDatasource.ds_type}
              onChange={e => setNewDatasource({ ...newDatasource, ds_type: e.target.value })}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-400 outline-none bg-white">
              <option value="prometheus">Prometheus</option>
            </select>
            <p className="text-xs text-slate-400 mt-1">当前仅支持 Prometheus，其他类型可通过插件扩展</p>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600 block mb-1">URL</label>
            <input type="text" value={newDatasource.url}
              onChange={e => setNewDatasource({ ...newDatasource, url: e.target.value })}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono focus:border-indigo-400 outline-none"
              placeholder="http://prometheus:9090" />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={newDatasource.auth_enabled}
              onChange={e => setNewDatasource({ ...newDatasource, auth_enabled: e.target.checked })}
              className="rounded border-slate-300" />
            <span className="text-sm font-medium text-slate-600">启用 Basic 认证</span>
          </label>
          {newDatasource.auth_enabled && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-500 block mb-1">用户名</label>
                <input type="text" value={newDatasource.auth_username}
                  onChange={e => setNewDatasource({ ...newDatasource, auth_username: e.target.value })}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-400 outline-none" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 block mb-1">密码</label>
                <input type="password" value={newDatasource.auth_password}
                  onChange={e => setNewDatasource({ ...newDatasource, auth_password: e.target.value })}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-400 outline-none" />
              </div>
            </div>
          )}
        </div>
        <div className="flex gap-3 mt-6">
          <button onClick={() => setShowModal(null)}
            className="flex-1 py-2.5 border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 text-sm font-medium">
            取消
          </button>
          <button onClick={saveDatasource}
            className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 text-sm font-medium">
            保存
          </button>
        </div>
      </div>
    </div>
  )

  const renderEditMetricsModal = () => {
    if (metricEditorIdx === null || metricEditorIdx === undefined) return null
    const config = pluginConfigs[metricEditorIdx]
    if (!config) return null
    const queries = [...(config.extra_config?.queries || [])]

    const updateQuery = (qi, field, value) => {
      const updated = [...pluginConfigs]
      const qs = [...(updated[metricEditorIdx].extra_config?.queries || [])]
      if (!qs[qi]) return
      qs[qi] = { ...qs[qi], [field]: value }
      updated[metricEditorIdx] = {
        ...updated[metricEditorIdx],
        extra_config: { ...updated[metricEditorIdx].extra_config, queries: qs }
      }
      setPluginConfigs(updated)
    }

    const addQuery = () => {
      const updated = [...pluginConfigs]
      const qs = [...(updated[metricEditorIdx].extra_config?.queries || [])]
      qs.push({ name: '', promql: '', threshold: '', severity: 'critical' })
      updated[metricEditorIdx] = {
        ...updated[metricEditorIdx],
        extra_config: { ...updated[metricEditorIdx].extra_config, queries: qs }
      }
      setPluginConfigs(updated)
    }

    const removeQuery = (qi) => {
      const updated = [...pluginConfigs]
      const qs = [...(updated[metricEditorIdx].extra_config?.queries || [])]
      updated[metricEditorIdx] = {
        ...updated[metricEditorIdx],
        extra_config: { ...updated[metricEditorIdx].extra_config, queries: qs.filter((_, i) => i !== qi) }
      }
      setPluginConfigs(updated)
    }

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        onClick={() => { setShowModal(null); setMetricEditorIdx(null) }}>
        <div className="bg-white rounded-xl w-full max-w-2xl max-h-[80vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
          <h3 className="text-lg font-bold mb-1">自定义指标查询</h3>
          <p className="text-sm text-slate-500 mb-4">配置PromQL查询，<code>{'{instance}'}</code> 会被替换为实际实例地址</p>

          <div className="space-y-4">
            {queries.map((q, qi) => (
              <div key={qi} className="border rounded-xl p-4 bg-slate-50/50">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-sm font-medium text-slate-600">查询 #{qi + 1}</span>
                  <button onClick={() => removeQuery(qi)}
                    className="text-rose-500 hover:text-rose-700 text-xs flex items-center gap-1">
                    <Trash2 size={14} /> 删除
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-slate-500 block mb-1">查询名称</label>
                    <input type="text" value={q.name}
                      onChange={e => updateQuery(qi, 'name', e.target.value)}
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-400 outline-none bg-white"
                      placeholder="如: CPU使用率" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-500 block mb-1">阈值</label>
                    <input type="number" value={q.threshold || ''}
                      onChange={e => updateQuery(qi, 'threshold', e.target.value)}
                      className="w-full border border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-400 outline-none bg-white"
                      placeholder="可选" />
                  </div>
                  <div className="col-span-2">
                    <label className="text-xs font-medium text-slate-500 block mb-1">PromQL 查询语句</label>
                    <textarea value={q.promql}
                      onChange={e => updateQuery(qi, 'promql', e.target.value)}
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono focus:border-indigo-400 outline-none bg-white"
                      rows="2" placeholder='如: 100 - avg(rate(node_cpu_seconds_total{mode="idle",instance="{instance}"}[5m])) * 100' />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-500 block mb-1">严重级别</label>
                    <select value={q.severity || 'critical'}
                      onChange={e => updateQuery(qi, 'severity', e.target.value)}
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:border-indigo-400 outline-none bg-white">
                      <option value="critical">严重 (Critical)</option>
                      <option value="warning">警告 (Warning)</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <button onClick={addQuery}
            className="mt-4 w-full border-2 border-dashed border-slate-300 rounded-xl py-3 text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition flex items-center justify-center gap-2 text-sm font-medium">
            <Plus size={14} /> 添加查询
          </button>

          <div className="flex gap-3 mt-4">
            <button onClick={() => { setShowModal(null); setMetricEditorIdx(null) }}
              className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 text-sm font-medium">
              完成
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top Navigation */}
      <div className="gradient-header sticky top-0 z-40 shadow-lg shadow-indigo-500/10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/15 backdrop-blur rounded-xl flex items-center justify-center ring-1 ring-white/20">
              <Shield size={22} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-wide">Patrol 巡检系统</h1>
              <p className="text-xs text-indigo-200/80">自动化运维巡检平台</p>
            </div>
          </div>
          <div className="flex items-center gap-5 text-sm">
            <div className="flex items-center gap-6 bg-white/10 backdrop-blur rounded-xl px-4 py-1.5 ring-1 ring-white/10">
              <span className="flex items-center gap-1.5 text-indigo-100">
                <Server size={14} className="text-indigo-300" /> {stats.total_projects}
                <span className="text-indigo-300/60 ml-0.5">项目</span>
              </span>
              <span className="w-px h-4 bg-white/10" />
              <span className="flex items-center gap-1.5 text-indigo-100">
                <FileText size={14} className="text-indigo-300" /> {stats.total_records}
                <span className="text-indigo-300/60 ml-0.5">记录</span>
              </span>
              <span className="w-px h-4 bg-white/10" />
              <span className="flex items-center gap-1.5 text-indigo-100">
                <RefreshCw size={14} className="text-indigo-300" /> {stats.recent_records}
                <span className="text-indigo-300/60 ml-0.5">近7天</span>
              </span>
              {stats.abnormal_today > 0 && (
                <>
                  <span className="w-px h-4 bg-white/10" />
                  <span className="flex items-center gap-1.5 text-rose-300 font-semibold">
                    <AlertTriangle size={14} /> {stats.abnormal_today}
                    <span className="text-rose-300/60 ml-0.5">异常</span>
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Error / Success banners */}
      {error && (
        <div className="max-w-7xl mx-auto px-6 mt-4 animate-slide-up">
          <div className="bg-rose-50 border border-rose-200 text-rose-700 px-5 py-3 rounded-xl text-sm flex items-center gap-2 shadow-sm">
            <XCircle size={16} className="shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto font-bold text-rose-400 hover:text-rose-600">&times;</button>
          </div>
        </div>
      )}
      {success && (
        <div className="max-w-7xl mx-auto px-6 mt-4 animate-slide-up">
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-5 py-3 rounded-xl text-sm flex items-center gap-2 shadow-sm">
            <CheckCircle size={16} className="shrink-0" />
            <span>{success}</span>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Tab Navigation */}
        <div className="flex gap-1.5 mb-6 overflow-x-auto pb-2 bg-white rounded-2xl shadow-sm border border-slate-200/60 p-1.5">
          {tabs.map(tab => {
            const Icon = tab.icon
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-200
                  ${activeTab === tab.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 scale-[1.02]' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-800'}`}>
                <Icon size={16} /> {tab.label}
              </button>
            )
          })}
        </div>

        {/* Content */}
        <div className="min-h-96">
          {activeTab === 'projects' && renderProjects()}
          {activeTab === 'plugins' && renderPlugins()}
          {activeTab === 'datasources' && renderDatasources()}
          {activeTab === 'channels' && renderChannels()}
          {activeTab === 'notification-logs' && renderNotificationLogs()}
          {activeTab === 'schedules' && renderSchedules()}
          {activeTab === 'records' && renderRecords()}
          {activeTab === 'report' && renderReport()}
          {activeTab === 'settings' && renderSettings()}
        </div>
      </div>

      {/* Modals */}
      {(showModal === 'addProject' || showModal === 'editProject') && renderAddProjectModal()}
      {showModal === 'addPlugin' && renderAddPluginModal()}
      {(showModal === 'addChannel' || showModal === 'editChannel') && renderAddChannelModal()}
      {showModal === 'addDatasource' && renderAddDatasourceModal()}
      {showModal === 'editMetrics' && renderEditMetricsModal()}
      {showModal === 'addSchedule' && renderScheduleModal()}

      {/* Loading overlay */}
      {loading && (
        <div className="fixed inset-0 modal-backdrop flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-5 flex items-center gap-3 shadow-2xl animate-slide-up">
            <RefreshCw size={20} className="animate-spin text-indigo-600" />
            <span className="text-sm text-slate-600 font-medium">处理中...</span>
          </div>
        </div>
      )}
    </div>
  )
}