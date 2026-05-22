import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import {
  Sparkles, FileText, Clock, Globe, Mic, ChevronDown,
  Play, Pause, Download, Video, Loader2, CheckCircle2,
  AlertCircle, ArrowRight, RefreshCw, Wand2, Image as ImageIcon,
  Volume2, Film, Zap
} from 'lucide-react'
import { useStore } from '@/store/useStore'
import {
  generateScript, generateSceneAsset, renderVideo,
  getRenderStatus, getVoices, type VoiceOption
} from '@/lib/api'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const DURATIONS = [
  { label: '1 min (~10 scenes)', value: 1 },
  { label: '1.5 min (~15 scenes)', value: 1.5 },
  { label: '2 min (~20 scenes)', value: 2 },
  { label: '2.5 min (~25 scenes)', value: 2.5 },
  { label: '3 min (~30 scenes)', value: 3 },
]

const LANGUAGES = [
  { label: '🇺🇸 English', value: 'en' },
  { label: '🇸🇦 Arabic', value: 'ar' },
]

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function StepIndicator({ current }: { current: string }) {
  const steps = [
    { id: 'input', label: 'Configure', icon: Wand2 },
    { id: 'preview', label: 'Preview', icon: Film },
    { id: 'render', label: 'Export', icon: Download },
  ]
  const idx = steps.findIndex(s => s.id === current)
  return (
    <div className="flex items-center gap-2">
      {steps.map((step, i) => {
        const Icon = step.icon
        const active = i === idx
        const done = i < idx
        return (
          <div key={step.id} className="flex items-center gap-2">
            <div className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all',
              active && 'bg-brand-500 text-white',
              done && 'bg-brand-500/20 text-brand-400',
              !active && !done && 'bg-white/5 text-slate-500'
            )}>
              <Icon size={14} />
              <span className="hidden sm:inline">{step.label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={cn('w-8 h-px', done ? 'bg-brand-500/50' : 'bg-white/10')} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function Select({
  value, onChange, options, label
}: {
  value: string | number
  onChange: (v: any) => void
  options: { label: string; value: string | number }[]
  label: string
}) {
  return (
    <div className="relative">
      <label className="block text-xs text-slate-400 mb-1.5 font-medium">{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          className="input-field appearance-none pr-10 cursor-pointer"
        >
          {options.map(o => (
            <option key={o.value} value={o.value} className="bg-dark-800">{o.label}</option>
          ))}
        </select>
        <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
      </div>
    </div>
  )
}

function ProviderBadge({ provider }: { provider: string }) {
  const map: Record<string, { label: string; color: string }> = {
    gemini: { label: 'Gemini', color: 'text-blue-400 bg-blue-400/10' },
    huggingface: { label: 'HuggingFace', color: 'text-orange-400 bg-orange-400/10' },
    placeholder: { label: 'Placeholder', color: 'text-slate-400 bg-slate-400/10' },
    elevenlabs: { label: 'ElevenLabs', color: 'text-purple-400 bg-purple-400/10' },
    edge: { label: 'Edge-TTS', color: 'text-green-400 bg-green-400/10' },
  }
  const info = map[provider] || { label: provider, color: 'text-slate-400 bg-slate-400/10' }
  return (
    <span className={cn('text-[10px] font-mono px-1.5 py-0.5 rounded', info.color)}>
      {info.label}
    </span>
  )
}

// ─── Scene Card ───────────────────────────────────────────────────────────────

function SceneCard({ scene, asset, idx }: { scene: any; asset?: any; idx: number }) {
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const apiBase = import.meta.env.VITE_API_URL || ''

  const toggleAudio = () => {
    if (!asset?.audio_url) return
    if (!audioRef.current) {
      audioRef.current = new Audio(apiBase + asset.audio_url)
      audioRef.current.onended = () => setPlaying(false)
    }
    if (playing) {
      audioRef.current.pause()
      setPlaying(false)
    } else {
      audioRef.current.play()
      setPlaying(true)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04 }}
      className="scene-card"
    >
      <div className="flex gap-3">
        {/* Image */}
        <div className="w-20 h-28 rounded-lg overflow-hidden flex-shrink-0 bg-dark-700 relative">
          {asset?.image_url ? (
            <img
              src={apiBase + asset.image_url}
              alt={`Scene ${idx + 1}`}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              {asset === undefined ? (
                <div className="shimmer-bg w-full h-full absolute inset-0" />
              ) : (
                <ImageIcon size={20} className="text-slate-600" />
              )}
            </div>
          )}
          <div className="absolute top-1 left-1 bg-black/60 text-white text-[10px] font-mono px-1 rounded">
            {idx + 1}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-200 leading-relaxed line-clamp-3 mb-2">
            {scene.narration}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            {asset?.image_provider && <ProviderBadge provider={asset.image_provider} />}
            {asset?.audio_provider && <ProviderBadge provider={asset.audio_provider} />}
            {asset?.audio_duration && (
              <span className="text-[10px] text-slate-500 font-mono">
                {asset.audio_duration.toFixed(1)}s
              </span>
            )}
          </div>
        </div>

        {/* Audio btn */}
        <button
          onClick={toggleAudio}
          disabled={!asset?.audio_url}
          className={cn(
            'flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-all',
            asset?.audio_url
              ? 'bg-brand-500/20 hover:bg-brand-500/40 text-brand-400'
              : 'bg-white/5 text-slate-600 cursor-not-allowed'
          )}
        >
          {playing ? <Pause size={14} /> : <Play size={14} />}
        </button>
      </div>

      {/* Image prompt */}
      <p className="mt-2 text-[11px] text-slate-600 font-mono line-clamp-1">
        📷 {scene.image_prompt}
      </p>
    </motion.div>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const store = useStore()
  const [voices, setVoices] = useState<{ elevenlabs: VoiceOption[]; edge_tts: VoiceOption[] }>({
    elevenlabs: [],
    edge_tts: [],
  })

  useEffect(() => {
    getVoices().then(setVoices).catch(() => {})
  }, [])

  // ── Generate Script ──────────────────────────────────────────────────────────
  const handleGenerateScript = async () => {
    if (store.mode === 'ai' && !store.topic.trim()) {
      toast.error('Please enter a topic first')
      return
    }
    if (store.mode === 'manual' && !store.manualScript.trim()) {
      toast.error('Please paste your script first')
      return
    }
    store.setGeneratingScript(true)
    try {
      const result = await generateScript({
        mode: store.mode,
        topic: store.topic,
        manual_script: store.manualScript,
        duration_minutes: Number(store.durationMinutes),
        language: store.language,
      })
      store.setScript(result.title, result.scenes)
      store.setStep('preview')
      toast.success(`✅ ${result.total_scenes} scenes generated!`)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Script generation failed')
    } finally {
      store.setGeneratingScript(false)
    }
  }

  // ── Generate All Assets ───────────────────────────────────────────────────────
  const handleGenerateAssets = async () => {
    store.setGeneratingAssets(true)
    store.setAssetsProgress(0)
    const total = store.scenes.length
    let done = 0

    const processScene = async (scene: any) => {
      try {
        const asset = await generateSceneAsset({
          session_id: store.sessionId,
          scene_index: scene.index,
          image_prompt: scene.image_prompt,
          narration: scene.narration,
          tts_provider: store.ttsProvider,
          voice_id: store.ttsProvider === 'elevenlabs' ? store.selectedVoiceId : undefined,
          edge_tts_voice: store.ttsProvider === 'edge' ? store.selectedEdgeVoice : undefined,
          language: store.language,
        })
        store.setSceneAsset(scene.index, asset)
      } catch {
        // handled per-scene
      } finally {
        done++
        store.setAssetsProgress(Math.round((done / total) * 100))
      }
    }

    // Process in batches of 4
    const chunks: any[][] = []
    for (let i = 0; i < store.scenes.length; i += 4) {
      chunks.push(store.scenes.slice(i, i + 4))
    }
    for (const chunk of chunks) {
      await Promise.all(chunk.map(processScene))
    }

    store.setGeneratingAssets(false)
    toast.success('All assets generated!')
  }

  // ── Render Video ──────────────────────────────────────────────────────────────
  const handleRender = async () => {
    const assetsReady = store.scenes.every(s => store.sceneAssets[s.index]?.success)
    if (!assetsReady) {
      toast.error('Generate all assets first!')
      return
    }

    store.setStep('render')
    store.setRenderStatus('queued', 0)

    const scenesPayload = store.scenes.map(s => {
      const asset = store.sceneAssets[s.index]
      const apiBase = import.meta.env.VITE_API_URL || ''
      return {
        scene_index: s.index,
        narration: s.narration,
        image_path: asset.image_url.replace('/static/', 'static/'),
        audio_path: asset.audio_url.replace('/static/', 'static/'),
        audio_duration: asset.audio_duration,
      }
    })

    try {
      await renderVideo({
        session_id: store.sessionId,
        title: store.title,
        scenes: scenesPayload,
        subtitle_style: 'bold',
      })

      // Poll status
      const poll = setInterval(async () => {
        try {
          const status = await getRenderStatus(store.sessionId)
          store.setRenderStatus(status.status as any, status.progress)
          if (status.status === 'done') {
            clearInterval(poll)
            store.setDownloadUrl(status.download_url || '')
            toast.success('🎬 Video ready!')
          } else if (status.status === 'failed') {
            clearInterval(poll)
            store.setRenderError(status.error || 'Render failed')
            toast.error('Render failed: ' + status.error)
          }
        } catch {
          clearInterval(poll)
        }
      }, 2000)
    } catch (e: any) {
      store.setRenderError(e?.message || 'Render start failed')
      toast.error('Failed to start render')
    }
  }

  const assetsCount = Object.values(store.sceneAssets).filter(a => a.success).length
  const allAssetsReady = store.scenes.length > 0 && assetsCount === store.scenes.length

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-white/5 bg-dark-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 flex items-center justify-center glow-blue">
              <Film size={18} className="text-white" />
            </div>
            <div>
              <h1 className="font-display font-bold text-white text-sm leading-none">AI Shorts Factory</h1>
              <p className="text-[10px] text-slate-500 mt-0.5">Cloud · Free · No GPU</p>
            </div>
          </div>
          <StepIndicator current={store.currentStep} />
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
        <AnimatePresence mode="wait">

          {/* ── STEP 1: INPUT ── */}
          {store.currentStep === 'input' && (
            <motion.div
              key="input"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* Hero */}
              <div className="text-center pt-4 pb-6">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-medium mb-4">
                  <Zap size={12} />
                  Powered by Gemini + ElevenLabs + MoviePy
                </div>
                <h2 className="text-4xl font-display font-bold text-white mb-3">
                  Create <span className="gradient-text">AI Videos</span> in Minutes
                </h2>
                <p className="text-slate-400 max-w-md mx-auto">
                  Generate stunning short-form videos with AI scripts, voiceovers, and cinematic effects — entirely cloud-based.
                </p>
              </div>

              <div className="grid lg:grid-cols-3 gap-6">
                {/* Left — main input */}
                <div className="lg:col-span-2 space-y-5">
                  {/* Mode toggle */}
                  <div className="card">
                    <div className="flex gap-2 mb-5">
                      {(['ai', 'manual'] as const).map(m => (
                        <button
                          key={m}
                          onClick={() => store.setMode(m)}
                          className={cn(
                            'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all',
                            store.mode === m
                              ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/20'
                              : 'bg-white/5 text-slate-400 hover:bg-white/10'
                          )}
                        >
                          {m === 'ai' ? <Sparkles size={15} /> : <FileText size={15} />}
                          {m === 'ai' ? 'AI Topic' : 'Manual Script'}
                        </button>
                      ))}
                    </div>

                    {store.mode === 'ai' ? (
                      <div>
                        <label className="block text-xs text-slate-400 mb-1.5 font-medium">Video Topic</label>
                        <input
                          className="input-field"
                          placeholder="e.g. The Mystery of the Bermuda Triangle"
                          value={store.topic}
                          onChange={e => store.setTopic(e.target.value)}
                          onKeyDown={e => e.key === 'Enter' && handleGenerateScript()}
                        />
                        <p className="text-[11px] text-slate-600 mt-1.5">
                          Gemini will generate a full cinematic script with image prompts
                        </p>
                      </div>
                    ) : (
                      <div>
                        <label className="block text-xs text-slate-400 mb-1.5 font-medium">Paste Your Script</label>
                        <textarea
                          className="input-field resize-none"
                          rows={7}
                          placeholder="Paste your full script here. Gemini will split it into scenes and generate image prompts automatically..."
                          value={store.manualScript}
                          onChange={e => store.setManualScript(e.target.value)}
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Right — settings */}
                <div className="space-y-4">
                  <div className="card space-y-4">
                    <h3 className="font-display font-semibold text-sm text-white flex items-center gap-2">
                      <Clock size={15} className="text-brand-400" /> Settings
                    </h3>
                    <Select
                      label="Duration"
                      value={store.durationMinutes}
                      onChange={v => store.setDuration(Number(v))}
                      options={DURATIONS}
                    />
                    <Select
                      label="Language"
                      value={store.language}
                      onChange={v => { store.setLanguage(v); if (v === 'ar') { store.setTtsProvider('edge'); store.setSelectedEdgeVoice('ar-EG-SalmaNeural') } }}
                      options={LANGUAGES}
                    />
                    <div>
                      <label className="block text-xs text-slate-400 mb-1.5 font-medium">Voice Engine</label>
                      <div className="flex gap-2">
                        {(['elevenlabs', 'edge'] as const).map(p => (
                          <button
                            key={p}
                            onClick={() => store.setTtsProvider(p)}
                            className={cn(
                              'flex-1 text-xs py-2 rounded-lg font-medium transition-all',
                              store.ttsProvider === p
                                ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                                : 'bg-white/5 text-slate-500 hover:bg-white/8'
                            )}
                          >
                            {p === 'elevenlabs' ? '🎙 ElevenLabs' : '🔊 Edge-TTS'}
                          </button>
                        ))}
                      </div>
                    </div>

                    {store.ttsProvider === 'elevenlabs' && voices.elevenlabs.length > 0 && (
                      <Select
                        label="ElevenLabs Voice"
                        value={store.selectedVoiceId}
                        onChange={store.setSelectedVoiceId}
                        options={voices.elevenlabs.map(v => ({ label: `${v.name} (${v.gender})`, value: v.id }))}
                      />
                    )}
                    {store.ttsProvider === 'edge' && voices.edge_tts.length > 0 && (
                      <Select
                        label="Edge-TTS Voice"
                        value={store.selectedEdgeVoice}
                        onChange={store.setSelectedEdgeVoice}
                        options={voices.edge_tts.filter(v => v.lang === store.language || !v.lang).map(v => ({ label: v.name, value: v.id }))}
                      />
                    )}
                  </div>

                  {/* Info cards */}
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { icon: '🖼', label: 'Gemini Imagen', sub: '+ HF fallback' },
                      { icon: '🎙', label: 'ElevenLabs', sub: '+ Edge-TTS' },
                      { icon: '🎬', label: 'Ken Burns', sub: 'Auto effect' },
                      { icon: '📱', label: '9:16 Format', sub: 'Shorts ready' },
                    ].map(item => (
                      <div key={item.label} className="card p-3">
                        <div className="text-lg mb-1">{item.icon}</div>
                        <div className="text-[11px] font-medium text-slate-300">{item.label}</div>
                        <div className="text-[10px] text-slate-600">{item.sub}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-center pt-2">
                <button
                  onClick={handleGenerateScript}
                  disabled={store.isGeneratingScript}
                  className="btn-primary flex items-center gap-3 text-base px-10 py-4 glow-blue"
                >
                  {store.isGeneratingScript ? (
                    <><Loader2 size={20} className="animate-spin" /> Generating Script...</>
                  ) : (
                    <><Wand2 size={20} /> Generate Script <ArrowRight size={16} /></>
                  )}
                </button>
              </div>
            </motion.div>
          )}

          {/* ── STEP 2: PREVIEW ── */}
          {store.currentStep === 'preview' && (
            <motion.div
              key="preview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* Header bar */}
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <h2 className="text-2xl font-display font-bold text-white">{store.title}</h2>
                  <p className="text-slate-400 text-sm mt-1">
                    {store.scenes.length} scenes · {store.language === 'ar' ? 'Arabic' : 'English'}
                    {assetsCount > 0 && ` · ${assetsCount}/${store.scenes.length} assets ready`}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button onClick={() => store.setStep('input')} className="btn-secondary flex items-center gap-2 text-sm">
                    <RefreshCw size={14} /> Back
                  </button>
                  <button
                    onClick={handleGenerateAssets}
                    disabled={store.isGeneratingAssets}
                    className="btn-primary flex items-center gap-2 text-sm px-5 py-2.5"
                  >
                    {store.isGeneratingAssets ? (
                      <><Loader2 size={15} className="animate-spin" /> Generating... {store.assetsProgress}%</>
                    ) : (
                      <><Sparkles size={15} /> Generate All Assets</>
                    )}
                  </button>
                  {allAssetsReady && (
                    <button
                      onClick={handleRender}
                      className="btn-primary flex items-center gap-2 text-sm px-5 py-2.5 bg-gradient-to-r from-brand-500 to-violet-500"
                    >
                      <Video size={15} /> Render Video
                    </button>
                  )}
                </div>
              </div>

              {/* Progress bar */}
              {store.isGeneratingAssets && (
                <div className="card">
                  <div className="flex justify-between text-xs text-slate-400 mb-2">
                    <span>Generating assets...</span>
                    <span>{store.assetsProgress}%</span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-brand-500 to-violet-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${store.assetsProgress}%` }}
                      transition={{ ease: 'easeOut' }}
                    />
                  </div>
                </div>
              )}

              {/* Scene grid */}
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {store.scenes.map((scene, i) => (
                  <SceneCard
                    key={scene.index}
                    scene={scene}
                    asset={store.sceneAssets[scene.index]}
                    idx={i}
                  />
                ))}
              </div>
            </motion.div>
          )}

          {/* ── STEP 3: RENDER ── */}
          {store.currentStep === 'render' && (
            <motion.div
              key="render"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center min-h-[60vh] gap-8"
            >
              <div className="card max-w-md w-full text-center p-8 glow-blue">
                {store.renderStatus === 'done' ? (
                  <>
                    <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-4">
                      <CheckCircle2 size={40} className="text-green-400" />
                    </div>
                    <h3 className="text-2xl font-display font-bold text-white mb-2">Video Ready!</h3>
                    <p className="text-slate-400 mb-6">Your AI-generated video has been compiled successfully.</p>
                    <a
                      href={(import.meta.env.VITE_API_URL || '') + store.downloadUrl}
                      download
                      className="btn-primary inline-flex items-center gap-3 text-base px-8 py-3.5 w-full justify-center"
                    >
                      <Download size={20} /> Download MP4
                    </a>
                    <button
                      onClick={() => { store.reset() }}
                      className="btn-secondary mt-3 w-full text-sm flex items-center justify-center gap-2"
                    >
                      <RefreshCw size={14} /> Create New Video
                    </button>
                  </>
                ) : store.renderStatus === 'failed' ? (
                  <>
                    <div className="w-20 h-20 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
                      <AlertCircle size={40} className="text-red-400" />
                    </div>
                    <h3 className="text-xl font-display font-bold text-white mb-2">Render Failed</h3>
                    <p className="text-red-400 text-sm mb-6">{store.renderError}</p>
                    <button onClick={() => store.setStep('preview')} className="btn-primary w-full">
                      Go Back & Retry
                    </button>
                  </>
                ) : (
                  <>
                    <div className="w-20 h-20 rounded-full bg-brand-500/10 flex items-center justify-center mx-auto mb-4 relative">
                      <Film size={36} className="text-brand-400" />
                      <div className="absolute inset-0 rounded-full border-2 border-brand-500/30 animate-ping" />
                    </div>
                    <h3 className="text-xl font-display font-bold text-white mb-2">Rendering Video</h3>
                    <p className="text-slate-400 text-sm mb-6">
                      Applying Ken Burns effects, subtitles, and compiling your scenes...
                    </p>
                    <div className="h-3 bg-white/5 rounded-full overflow-hidden mb-2">
                      <motion.div
                        className="h-full bg-gradient-to-r from-brand-500 to-violet-500 rounded-full progress-pulse"
                        animate={{ width: `${store.renderProgress}%` }}
                        transition={{ ease: 'easeOut' }}
                      />
                    </div>
                    <p className="text-xs text-slate-500 font-mono">{store.renderProgress}% complete</p>
                  </>
                )}
              </div>

              {/* Scene thumbnail strip */}
              {store.scenes.length > 0 && (
                <div className="flex gap-2 overflow-x-auto pb-2 max-w-2xl w-full">
                  {store.scenes.map((scene, i) => {
                    const asset = store.sceneAssets[scene.index]
                    const apiBase = import.meta.env.VITE_API_URL || ''
                    return (
                      <div key={i} className="flex-shrink-0 w-14 h-20 rounded-lg overflow-hidden bg-dark-700">
                        {asset?.image_url ? (
                          <img src={apiBase + asset.image_url} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <div className="shimmer-bg w-full h-full" />
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-4 text-center text-xs text-slate-600">
        AI Shorts & Video Factory · 100% Cloud · Free Tier · No GPU Required
      </footer>
    </div>
  )
}
