'use client'

import { useState, useEffect } from 'react'
import { containerlabApi, switchesApi, SwitchData } from '@/lib/api'
import { Map, RefreshCw, Plus, Server, Link as LinkIcon } from 'lucide-react'
import toast from 'react-hot-toast'

export default function TopologyPage() {
  const [topologies, setTopologies] = useState<any[]>([])
  const [switches, setSwitches] = useState<SwitchData[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<any>(null)

  const load = () => {
    Promise.all([containerlabApi.list(), switchesApi.list()])
      .then(([t, s]) => { setTopologies(t); setSwitches(s) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleScan = async () => {
    try {
      const result = await containerlabApi.scan()
      toast.success(`Found ${result.topologies_found} topology/topologies`)
      load()
    } catch (e: any) { toast.error(e.message) }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this topology?')) return
    try {
      await containerlabApi.delete(id)
      toast.success('Topology deleted')
      load()
    } catch (e: any) { toast.error(e.message) }
  }

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Topology</h1>
          <p className="text-slate-400 mt-1">Network topology visualization from Containerlab</p>
        </div>
        <button onClick={handleScan} className="btn btn-primary btn-sm">
          <RefreshCw className="w-4 h-4" /> Scan Topologies
        </button>
      </div>

      {loading ? (
        <div className="card p-8"><div className="skeleton h-48 w-full" /></div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Topology list */}
          <div className="lg:col-span-1 space-y-3">
            {topologies.length === 0 && (
              <div className="card text-center py-8 text-slate-500">
                <Map className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No topologies discovered</p>
                <p className="text-xs mt-1">Scan for Containerlab topologies</p>
              </div>
            )}
            {topologies.map(t => (
              <div key={t.id}
                className={`card cursor-pointer transition-all ${selected?.id === t.id ? 'border-blue-500/50' : ''}`}
                onClick={() => setSelected(t)}>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium text-white text-sm">{t.name}</h3>
                    <p className="text-xs text-slate-500 mt-1">{t.node_count} nodes · {t.link_count} links</p>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); handleDelete(t.id) }}
                    className="text-slate-600 hover:text-red-400 transition-colors text-xs">
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Topology detail / visualization */}
          <div className="lg:col-span-2">
            {selected ? (
              <div className="card">
                <h2 className="font-semibold text-white mb-4">{selected.name}</h2>

                {/* Nodes */}
                <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                  <Server className="w-4 h-4" /> Nodes ({selected.node_count})
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-6">
                  {(selected.topology_data?.nodes || []).map((node: any, i: number) => (
                    <div key={i} className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                      <p className="text-sm font-medium text-white truncate">{node.name}</p>
                      <p className="text-xs text-slate-500">{node.kind}</p>
                      {node.mgmt_ip && <p className="text-xs font-mono text-blue-400 mt-1">{node.mgmt_ip}</p>}
                    </div>
                  ))}
                </div>

                {/* Links */}
                {selected.topology_data?.links?.length > 0 && (
                  <>
                    <h3 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                      <LinkIcon className="w-4 h-4" /> Links ({selected.link_count})
                    </h3>
                    <div className="space-y-1">
                      {(selected.topology_data?.links || []).map((link: any, i: number) => (
                        <div key={i} className="text-xs text-slate-400 py-1 px-2 rounded bg-slate-800/30">
                          {link.endpoints?.join(' <-> ') || JSON.stringify(link)}
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {/* Topology visual (ASCII) */}
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-slate-400 mb-2">Visualization</h3>
                  <pre className="text-xs text-slate-500 leading-relaxed">
                    {generateAsciiTopology(selected.topology_data)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="card flex items-center justify-center py-16 text-slate-500">
                <div className="text-center">
                  <Map className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Select a topology to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function generateAsciiTopology(data: any): string {
  if (!data?.nodes) return 'No topology data'
  const nodes = data.nodes.map((n: any) => n.name)
  const links = data.links || []

  let viz = `╔══ ${data.name || 'Topology'} ══╗\n\n`
  viz += `  Nodes: ${data.nodes.length}\n`
  viz += `  Links: ${data.links.length}\n\n`

  // Show nodes
  viz += `  ┌─ Devices ─────────────┐\n`
  for (const node of data.nodes) {
    const mgmt = node.mgmt_ip ? ` [${node.mgmt_ip}]` : ''
    viz += `  │  • ${node.name.padEnd(20)} ${node.kind}${mgmt}\n`
  }
  viz += `  └────────────────────────┘\n`

  // Show connections
  if (links.length > 0) {
    viz += `\n  ┌─ Connections ───────────┐\n`
    for (const link of links) {
      const endpoints = link.endpoints?.join(' ─── ') || 'unknown'
      viz += `  │  ${endpoints}\n`
    }
    viz += `  └────────────────────────┘\n`
  }

  return viz
}
