'use client'

import { useState, useEffect } from 'react'
import { dashboardApi, switchesApi, SwitchData } from '@/lib/api'
import { timeAgo } from '@/lib/utils'
import { Activity, RefreshCw, Cpu, Memory, Wifi, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function MetricsPage() {
  const [switches, setSwitches] = useState<SwitchData[]>([])
  const [healthSummary, setHealthSummary] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    Promise.all([switchesApi.list(), dashboardApi.healthSummary()])
      .then(([s, h]) => { setSwitches(s); setHealthSummary(h) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleRefresh = async () => {
    toast.success('Refreshing health data...')
    load()
  }

  if (loading) return <div className="card p-8"><div className="skeleton h-96 w-full" /></div>

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Metrics & Health</h1>
          <p className="text-slate-400 mt-1">Real-time device health monitoring</p>
        </div>
        <button onClick={handleRefresh} className="btn btn-secondary btn-sm">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricStatCard icon={<Cpu className="w-5 h-5" />} label="Avg CPU"
          value={avgMetric(healthSummary, 'cpu_usage')} unit="%" color="blue" />
        <MetricStatCard icon={<Memory className="w-5 h-5" />} label="Avg Memory"
          value={avgMetric(healthSummary, 'memory_usage')} unit="%" color="purple" />
        <MetricStatCard icon={<Wifi className="w-5 h-5" />} label="Interfaces Up"
          value={sumMetric(healthSummary, 'interfaces_up')} unit={`/ ${sumMetric(healthSummary, 'interfaces_up') + sumMetric(healthSummary, 'interfaces_down')}`} color="green" />
        <MetricStatCard icon={<AlertTriangle className="w-5 h-5" />} label="Total Findings"
          value={sumMetric(healthSummary, 'open_findings')} unit="open" color="red" />
      </div>

      {/* Device health table */}
      <div className="card">
        <h2 className="font-semibold text-white mb-4">Device Health Details</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Device</th>
                <th>Status</th>
                <th>CPU</th>
                <th>Memory</th>
                <th>Interfaces</th>
                <th>Findings</th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {healthSummary.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-12 text-slate-500">No devices registered</td></tr>
              ) : healthSummary.map(d => (
                <tr key={d.switch_id}>
                  <td className="font-medium text-white">{d.hostname}</td>
                  <td>
                    <span className={`inline-flex items-center gap-1.5 text-sm ${
                      d.status === 'online' ? 'text-green-400' :
                      d.status === 'offline' ? 'text-red-400' : 'text-yellow-400'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        d.status === 'online' ? 'bg-green-400 pulse-dot' :
                        d.status === 'offline' ? 'bg-red-400' : 'bg-yellow-400'
                      }`} />
                      {d.status}
                    </span>
                  </td>
                  <td>
                    <MetricBar value={d.cpu_usage} color="blue" />
                  </td>
                  <td>
                    <MetricBar value={d.memory_usage} color="purple" />
                  </td>
                  <td className="text-sm">
                    <span className="text-green-400">{d.interfaces_up || 0}</span>
                    <span className="text-slate-500">/</span>
                    <span className="text-red-400">{d.interfaces_down || 0}</span>
                    <span className="text-slate-500"> down</span>
                  </td>
                  <td>
                    <span className={`badge text-xs ${
                      d.open_findings > 0 ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                      'bg-green-500/10 text-green-400 border-green-500/20'
                    }`}>
                      {d.open_findings || 0}
                    </span>
                  </td>
                  <td className="text-sm text-slate-400">{d.last_updated ? timeAgo(d.last_updated) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function MetricStatCard({ icon, label, value, unit, color }: {
  icon: React.ReactNode; label: string; value: number; unit: string; color: string
}) {
  const colors: Record<string, string> = {
    blue: 'text-blue-400', purple: 'text-purple-400', green: 'text-green-400', red: 'text-red-400'
  }
  return (
    <div className="card">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-black/20 ${colors[color]}`}>{icon}</div>
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider">{label}</p>
          <p className="text-xl font-bold text-white">
            {value !== null ? value : '—'}
            <span className="text-sm font-normal text-slate-500 ml-1">{unit}</span>
          </p>
        </div>
      </div>
    </div>
  )
}

function MetricBar({ value, color }: { value: number | null; color: string }) {
  if (value === null) return <span className="text-slate-500 text-sm">—</span>
  const colors: Record<string, string> = {
    blue: 'bg-blue-500', purple: 'bg-purple-500', green: 'bg-green-500', red: 'bg-red-500'
  }
  const barColor = value > 80 ? 'bg-red-500' : color === 'blue' ? 'bg-blue-500' : 'bg-purple-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 rounded-full bg-slate-700 overflow-hidden">
        <div className={`h-full ${barColor} rounded-full transition-all`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
      <span className="text-sm text-slate-400">{value}%</span>
    </div>
  )
}

function avgMetric(data: any[], key: string): number | null {
  const vals = data.filter(d => d[key] !== null).map(d => d[key])
  if (vals.length === 0) return null
  return Math.round((vals.reduce((a: number, b: number) => a + b, 0) / vals.length) * 10) / 10
}

function sumMetric(data: any[], key: string): number {
  return data.reduce((a: number, d: any) => a + (d[key] || 0), 0)
}
