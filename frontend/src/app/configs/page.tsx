'use client'

import { useState, useEffect } from 'react'
import { switchesApi, configsApi, SwitchData, ConfigBackupData } from '@/lib/api'
import { timeAgo } from '@/lib/utils'
import { FileText, Copy, Download, GitCompare, Search } from 'lucide-react'
import toast from 'react-hot-toast'

export default function ConfigsPage() {
  const [switches, setSwitches] = useState<SwitchData[]>([])
  const [selectedSwitch, setSelectedSwitch] = useState<number | null>(null)
  const [configs, setConfigs] = useState<ConfigBackupData[]>([])
  const [latestConfig, setLatestConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'view' | 'diff'>('view')
  const [backupA, setBackupA] = useState<number | null>(null)
  const [backupB, setBackupB] = useState<number | null>(null)
  const [diffResult, setDiffResult] = useState<any>(null)

  useEffect(() => {
    switchesApi.list().then(setSwitches).catch(() => {})
    setLoading(false)
  }, [])

  const loadConfigs = async (switchId: number) => {
    setSelectedSwitch(switchId)
    setLatestConfig(null)
    setDiffResult(null)
    const [configList, latest] = await Promise.all([
      configsApi.list(switchId),
      configsApi.latest(switchId),
    ])
    setConfigs(configList)
    setLatestConfig(latest)
  }

  const handleDiff = async () => {
    if (!backupA || !backupB) { toast.error('Select two backups to compare'); return }
    try {
      const result = await configsApi.diff(backupA, backupB)
      setDiffResult(result)
    } catch (e: any) { toast.error(e.message) }
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Configurations</h1>
          <p className="text-slate-400 mt-1">View, compare, and manage device configurations</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Switch selector sidebar */}
        <div className="lg:col-span-1 card">
          <h2 className="font-semibold text-white mb-3 text-sm">Select Device</h2>
          <div className="space-y-1">
            {switches.map(sw => (
              <button key={sw.id} onClick={() => loadConfigs(sw.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  selectedSwitch === sw.id ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                  'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}>
                {sw.hostname}
                <span className="block text-xs text-slate-500">{sw.ip_address}</span>
              </button>
            ))}
            {switches.length === 0 && <p className="text-slate-500 text-sm py-4 text-center">No switches</p>}
          </div>
        </div>

        {/* Config viewer */}
        <div className="lg:col-span-3 space-y-4">
          {!selectedSwitch ? (
            <div className="card flex items-center justify-center py-16 text-slate-500">
              <div className="text-center">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Select a device to view its configuration</p>
              </div>
            </div>
          ) : (
            <>
              {/* Tabs */}
              <div className="flex items-center justify-between">
                <div className="tabs">
                  <button className={`tab ${activeTab === 'view' ? 'active' : ''}`}
                    onClick={() => setActiveTab('view')}>View</button>
                  <button className={`tab ${activeTab === 'diff' ? 'active' : ''}`}
                    onClick={() => setActiveTab('diff')}>Diff</button>
                </div>
                {latestConfig?.config && (
                  <button onClick={() => handleCopy(latestConfig.config)}
                    className="btn btn-secondary btn-sm">
                    <Copy className="w-3.5 h-3.5" /> Copy
                  </button>
                )}
              </div>

              {/* View tab */}
              {activeTab === 'view' && (
                <div className="card">
                  {latestConfig?.config ? (
                    <>
                      <div className="flex items-center justify-between mb-3 text-sm text-slate-400">
                        <span>Backup #{latestConfig.backup_id} · {latestConfig.config_type}</span>
                        <span>{latestConfig.timestamp}</span>
                      </div>
                      <pre className="text-sm leading-relaxed">{latestConfig.config}</pre>
                    </>
                  ) : (
                    <p className="text-slate-500 text-center py-8">No config backup available. Sync the device first.</p>
                  )}
                </div>
              )}

              {/* Diff tab */}
              {activeTab === 'diff' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-slate-400 mb-1 block">Older Backup</label>
                      <select className="input select" value={backupA || ''}
                        onChange={e => setBackupA(parseInt(e.target.value))}>
                        <option value="">Select...</option>
                        {configs.map(c => (
                          <option key={c.id} value={c.id}>#{c.id} ({c.created_at})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-sm text-slate-400 mb-1 block">Newer Backup</label>
                      <select className="input select" value={backupB || ''}
                        onChange={e => setBackupB(parseInt(e.target.value))}>
                        <option value="">Select...</option>
                        {configs.map(c => (
                          <option key={c.id} value={c.id}>#{c.id} ({c.created_at})</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <button onClick={handleDiff} className="btn btn-primary">
                    <GitCompare className="w-4 h-4" /> Compare
                  </button>

                  {diffResult && (
                    <div className="card">
                      <div className="flex items-center justify-between mb-3 text-sm">
                        <span className="text-slate-400">
                          +{diffResult.additions} additions · -{diffResult.deletions} deletions
                        </span>
                      </div>
                      <pre className="text-sm">{diffResult.diff || 'No differences found'}</pre>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
