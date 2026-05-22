import { create } from 'zustand'
import type { Scene, SceneAsset } from '@/lib/api'

export type Step = 'input' | 'preview' | 'render'

interface AppState {
  // Session
  sessionId: string

  // Input
  mode: 'ai' | 'manual'
  topic: string
  manualScript: string
  durationMinutes: number
  language: string
  ttsProvider: 'elevenlabs' | 'edge'
  selectedVoiceId: string
  selectedEdgeVoice: string

  // Script
  title: string
  scenes: Scene[]
  isGeneratingScript: boolean

  // Assets
  sceneAssets: Record<number, SceneAsset>
  isGeneratingAssets: boolean
  assetsProgress: number

  // Render
  renderStatus: 'idle' | 'queued' | 'processing' | 'done' | 'failed'
  renderProgress: number
  downloadUrl: string
  renderError: string

  // Step
  currentStep: Step

  // Actions
  setMode: (m: 'ai' | 'manual') => void
  setTopic: (t: string) => void
  setManualScript: (s: string) => void
  setDuration: (d: number) => void
  setLanguage: (l: string) => void
  setTtsProvider: (p: 'elevenlabs' | 'edge') => void
  setSelectedVoiceId: (v: string) => void
  setSelectedEdgeVoice: (v: string) => void
  setScript: (title: string, scenes: Scene[]) => void
  setGeneratingScript: (v: boolean) => void
  setSceneAsset: (idx: number, asset: SceneAsset) => void
  setGeneratingAssets: (v: boolean) => void
  setAssetsProgress: (p: number) => void
  setRenderStatus: (s: AppState['renderStatus'], progress?: number) => void
  setDownloadUrl: (u: string) => void
  setRenderError: (e: string) => void
  setStep: (s: Step) => void
  reset: () => void
}

const newSessionId = () => `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

export const useStore = create<AppState>((set) => ({
  sessionId: newSessionId(),
  mode: 'ai',
  topic: '',
  manualScript: '',
  durationMinutes: 1,
  language: 'en',
  ttsProvider: 'edge',
  selectedVoiceId: '21m00Tcm4TlvDq8ikWAM',
  selectedEdgeVoice: 'en-US-AriaNeural',
  title: '',
  scenes: [],
  isGeneratingScript: false,
  sceneAssets: {},
  isGeneratingAssets: false,
  assetsProgress: 0,
  renderStatus: 'idle',
  renderProgress: 0,
  downloadUrl: '',
  renderError: '',
  currentStep: 'input',

  setMode: (m) => set({ mode: m }),
  setTopic: (t) => set({ topic: t }),
  setManualScript: (s) => set({ manualScript: s }),
  setDuration: (d) => set({ durationMinutes: d }),
  setLanguage: (l) => set({ language: l }),
  setTtsProvider: (p) => set({ ttsProvider: p }),
  setSelectedVoiceId: (v) => set({ selectedVoiceId: v }),
  setSelectedEdgeVoice: (v) => set({ selectedEdgeVoice: v }),
  setScript: (title, scenes) => set({ title, scenes, sceneAssets: {} }),
  setGeneratingScript: (v) => set({ isGeneratingScript: v }),
  setSceneAsset: (idx, asset) =>
    set((s) => ({ sceneAssets: { ...s.sceneAssets, [idx]: asset } })),
  setGeneratingAssets: (v) => set({ isGeneratingAssets: v }),
  setAssetsProgress: (p) => set({ assetsProgress: p }),
  setRenderStatus: (status, progress) =>
    set((s) => ({ renderStatus: status, renderProgress: progress ?? s.renderProgress })),
  setDownloadUrl: (u) => set({ downloadUrl: u }),
  setRenderError: (e) => set({ renderError: e }),
  setStep: (s) => set({ currentStep: s }),
  reset: () =>
    set({
      sessionId: newSessionId(),
      title: '',
      scenes: [],
      sceneAssets: {},
      renderStatus: 'idle',
      renderProgress: 0,
      downloadUrl: '',
      renderError: '',
      currentStep: 'input',
      assetsProgress: 0,
    }),
}))
