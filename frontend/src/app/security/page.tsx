'use client'

import { useState, useEffect } from 'react'
import { securityApi, SecurityFindingData } from '@/lib/api'
import { timeAgo, severityColor } from '@/lib/utils'
import { Shield, AlertTriangle, CheckCircle, RefreshCw, Search } from 'lucide-react'
import toast from 'react-hot-toast'

export default function SecurityPage() {
  const [findings, setFindings] = useState<SecurityFindingData[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [severityFilter, setSeverityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')

  const load = () => {
    setLoading(true)
    Promise.all([
      securityApi.list({ severity: severityFilter || undefined, status: statusFilter || undefined }),
      securityApi.stats(),
    ]).then(([f, s]) => {
      setFindings(f)
      setStats(s)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [severityFilter, statusFilter])

  const handleAuditAll = async () => {
    try {
      const result = await securityApi.auditAll()
      toast.success(`Audited ${result.audited} device(s)`)
      load()
    } catch (e: any) { toast.error(e.message) }
  }

  const handleResolve = async (id: number) => {
    try {
      await securityApi.resolve(id, 'resolved')
      toast.success('Finding resolved')
      load()
    } catch (e: any) { toast.error(e.message) }
  }

  const filtered = findings.filter(f =>
    f.title.toLowerCase().includes(search.toLowerCase())
  )

  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  const sorted = [...filtered].sort((a, b) =>
    (severityOrder[a.severity as keyof typeof severityOrder] ?? 99) -
    (severityOrder[b.severity as keyof typeof severityOrder] ?? 99)
  )

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Security</h1>
          <p className="text-slate-400 mt-1">Security audits, CVE scanning, and compliance checks</p>
        </div>
        <button onClick={handleAuditAll} className="btn btn-primary btn-sm">
          <RefreshCw className="w-4 h-4" /> Audit All
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatBadge label="Total" value={stats.total} color="text-white" bg="bg-slate-800" />
          <StatBadge label="Critical" value={stats.by_severity?.critical || 0} color="text-red-400" bg="bg-red-500/5" />
          <StatBadge label="High" value={stats.by_severity?.high || 0} color="text-orange-400" bg="bg-orange-500/5" />
          <StatBadge label="Medium" value={stats.by_severity?.medium || 0} color="text-yellow-400" bg="bg-yellow-500/5" />
          <StatBadge label="Open" value={stats.by_status?.open || 0} color="text-blue-400" bg="bg-blue-500/5" />
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input className="input pl-10" placeholder="Search findings..." value={search}
            onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="input select w-36" value={severityFilter}
          onChange={e => setSeverityFilter(e.target.value)}>
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select className="input select w-32" value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}>
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      {/* Findings */}
      {loading ? (
        <div className="card p-8"><div className="skeleton h-64 w-full" /></div>
      ) : sorted.length === 0 ? (
        <div className="card text-center py-12 text-slate-500">
          <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No findings found. Run an audit to check for issues.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map(f => (
            <div key={f.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`badge text-xs ${severityColor(f.severity)}`}>{f.severity}</span>
                    {f.cve_id && <span className="badge bg-red-500/10 text-red-400 border-red-500/20 text-xs">{f.cve_id}</span>}
                    <span className="badge bg-slate-800 text-slate-400 border-slate-700 text-xs">{f.finding_type}</span>
                    <span className="text-xs text-slate-500">{timeAgo(f.created_at)}</span>
                  </div>
                  <h3 className="font-medium text-white mt-2">{f.title}</h3>
                  {f.description && <p className="text-sm text-slate-400 mt-1">{f.description}</p>}
                  {f.remediation && (
                    <div className="mt-2 p-2 rounded-lg bg-green-500/5 border border-green-500/10">
                      <p className="text-xs text-green-400 font-medium">Remediation:</p>
                      <p className="text-sm text-green-300/80">{f.remediation}</p>
                    </div>
                  )}
                </div>
                {f.status === 'open' && (
                  <button onClick={() => handleResolve(f.id)} className="btn btn-success btn-sm ml-3">
                    <CheckCircle className="w-3.5 h-3.5" /> Resolve
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function StatBadge({ label, value, color, bg }: {
  label: string; value: number; color: string; bg: string
}) {
  return (
    <div className={`card ${bg} py-3`}>
      <p className="text-xs text-slate-500 uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  )
}
