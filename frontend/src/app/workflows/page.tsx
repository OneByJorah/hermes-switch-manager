'use client'

import { useState, useEffect } from 'react'
import { workflowsApi, switchesApi, WorkflowData, SwitchData } from '@/lib/api'
import { timeAgo } from '@/lib/utils'
import { GitBranch, Plus, Play, CheckCircle, XCircle, ChevronRight, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

const STEP_LABELS: Record<string, string> = {
  discover: 'Discover',
  verify: 'Verify',
  propose: 'Propose',
  confirm: 'Confirm',
  execute: 'Execute',
  verify_done: 'Verify',
  document: 'Document',
}

const STEP_COLORS: Record<string, string> = {
  pending: 'border-slate-600 text-slate-400',
  running: 'border-blue-500 text-blue-400 bg-blue-500/5',
  completed: 'border-green-500 text-green-400 bg-green-500/5',
  failed: 'border-red-500 text-red-400 bg-red-500/5',
  rejected: 'border-orange-500 text-orange-400 bg-orange-500/5',
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowData[]>([])
  const [switches, setSwitches] = useState<SwitchData[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [selectedWf, setSelectedWf] = useState<number | null>(null)

  const load = () => {
    Promise.all([workflowsApi.list(), switchesApi.list()])
      .then(([w, s]) => { setWorkflows(w); setSwitches(s) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleAdvance = async (wf: WorkflowData) => {
    try {
      const result = await workflowsApi.advance(wf.id, true)
      toast.success(`Advanced to: ${result.status}`)
      load()
    } catch (e: any) { toast.error(e.message) }
  }

  const handleExecute = async (wfId: number, stepId: number) => {
    try {
      await workflowsApi.executeStep(wfId, stepId)
      toast.success('Step executed')
      load()
    } catch (e: any) { toast.error(e.message) }
  }

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Workflows</h1>
          <p className="text-slate-400 mt-1">IRIS-style change management workflow engine</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn btn-primary btn-sm">
          <Plus className="w-4 h-4" /> New Workflow
        </button>
      </div>

      {loading ? (
        <div className="card p-8"><div className="skeleton h-48 w-full" /></div>
      ) : workflows.length === 0 ? (
        <div className="card text-center py-12 text-slate-500">
          <GitBranch className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No workflows yet. Create one to manage network changes.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {workflows.map(wf => (
            <div key={wf.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-white">{wf.title}</h3>
                    <span className={`badge text-xs ${
                      wf.status === 'completed' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                      wf.status === 'failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                      'bg-blue-500/10 text-blue-400 border-blue-500/20'
                    }`}>
                      {wf.status}
                    </span>
                  </div>
                  {wf.description && <p className="text-sm text-slate-400 mt-1">{wf.description}</p>}
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                    {wf.created_by && <span>By: {wf.created_by}</span>}
                    {wf.ticket_ref && <span>Ticket: {wf.ticket_ref}</span>}
                    <span>{timeAgo(wf.created_at)}</span>
                  </div>
                </div>

                <div className="flex gap-2">
                  {wf.status !== 'completed' && wf.status !== 'failed' && (
                    <button onClick={() => handleAdvance(wf)} className="btn btn-primary btn-sm">
                      <Play className="w-3.5 h-3.5" /> Advance
                    </button>
                  )}
                </div>
              </div>

              {/* Workflow steps */}
              {wf.steps && wf.steps.length > 0 && (
                <div className="mt-4 flex items-center gap-2 flex-wrap">
                  {wf.steps.map((step, i) => (
                    <div key={step.id} className="flex items-center gap-2">
                      <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium ${STEP_COLORS[step.status] || STEP_COLORS.pending}`}>
                        {step.status === 'completed' && <CheckCircle className="w-3 h-3" />}
                        {step.status === 'failed' && <XCircle className="w-3 h-3" />}
                        {step.status === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
                        {STEP_LABELS[step.step_type] || step.step_type}
                      </div>
                      {i < wf.steps.length - 1 && <ChevronRight className="w-3 h-3 text-slate-600" />}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateWorkflowModal
          switches={switches}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); load() }}
        />
      )}
    </div>
  )
}

function CreateWorkflowModal({ switches, onClose, onCreated }: {
  switches: SwitchData[]; onClose: () => void; onCreated: () => void
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selectedSwitches, setSelectedSwitches] = useState<number[]>([])
  const [ticketRef, setTicketRef] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      await workflowsApi.create({
        title,
        description,
        switch_ids: selectedSwitches.join(','),
        ticket_ref: ticketRef,
      })
      toast.success('Workflow created')
      onCreated()
    } catch (err: any) { toast.error(err.message) }
    finally { setSaving(false) }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card w-full max-w-lg mx-4" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-white mb-4">Create Workflow</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Title *</label>
            <input className="input" required value={title} onChange={e => setTitle(e.target.value)}
              placeholder="e.g., Update OSPF config on core switches" />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Description</label>
            <textarea className="input" rows={2} value={description} onChange={e => setDescription(e.target.value)}
              placeholder="What change needs to be made?" />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Target Switches</label>
            <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">
              {switches.map(sw => (
                <label key={sw.id} className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-slate-800 cursor-pointer">
                  <input type="checkbox" checked={selectedSwitches.includes(sw.id)}
                    onChange={() => setSelectedSwitches(prev =>
                      prev.includes(sw.id) ? prev.filter(id => id !== sw.id) : [...prev, sw.id]
                    )} className="rounded border-slate-600" />
                  <span className="text-sm">{sw.hostname}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Ticket Reference</label>
            <input className="input" value={ticketRef} onChange={e => setTicketRef(e.target.value)}
              placeholder="e.g., INC-12345" />
          </div>
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Creating...' : 'Create Workflow'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
