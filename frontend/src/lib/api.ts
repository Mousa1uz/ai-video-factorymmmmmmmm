import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Scene {
  index: number
  narration: string
  image_prompt: string
  duration_hint: number
}

export interface ScriptResponse {
  title: string
  total_scenes: number
  estimated_duration: number
  scenes: Scene[]
}

export interface SceneAsset {
  scene_index: number
  image_url: string
  audio_url: string
  audio_duration: number
  image_provider: string
  audio_provider: string
  success: boolean
  error?: string
}

export interface RenderStatus {
  session_id: string
  status: 'queued' | 'processing' | 'done' | 'failed'
  progress: number
  download_url?: string
  error?: string
}

export interface VoiceOption {
  id: string
  name: string
  gender: string
  accent?: string
  lang?: string
}

// ─── API Calls ────────────────────────────────────────────────────────────────

export const generateScript = (payload: {
  mode: 'ai' | 'manual'
  topic?: string
  manual_script?: string
  duration_minutes: number
  language: string
}) => api.post<ScriptResponse>('/api/script/generate', payload).then(r => r.data)

export const generateSceneAsset = (payload: {
  session_id: string
  scene_index: number
  image_prompt: string
  narration: string
  tts_provider: string
  voice_id?: string
  edge_tts_voice?: string
  language: string
}) => api.post<SceneAsset>('/api/assets/generate-scene', payload).then(r => r.data)

export const renderVideo = (payload: {
  session_id: string
  title: string
  scenes: Array<{
    scene_index: number
    narration: string
    image_path: string
    audio_path: string
    audio_duration: number
  }>
  subtitle_style: string
}) => api.post<RenderStatus>('/api/video/render', payload).then(r => r.data)

export const getRenderStatus = (session_id: string) =>
  api.get<RenderStatus>(`/api/video/status/${session_id}`).then(r => r.data)

export const getVoices = () =>
  api.get<{ elevenlabs: VoiceOption[]; edge_tts: VoiceOption[] }>('/api/assets/voices').then(r => r.data)
