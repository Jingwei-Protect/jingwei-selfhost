import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocale } from '../i18n/LocaleContext'

const PLAYLIST = [
  '/music/saltwater-refrain.mp3',
  '/music/saltwater-ukulele.mp3',
  '/music/seaglass-chords.mp3',
] as const

const STORAGE_KEY = 'jw-sea-music-track'

function loadTrackIndex(): number {
  try {
    const v = parseInt(sessionStorage.getItem(STORAGE_KEY) ?? '0', 10)
    if (v >= 0 && v < PLAYLIST.length) return v
  } catch { /* ignore */ }
  return 0
}

function saveTrackIndex(index: number) {
  try {
    sessionStorage.setItem(STORAGE_KEY, String(index))
  } catch { /* ignore */ }
}

/** Minimal ambient player for 精卫之海 — no track titles shown. */
export default function SeaMusicPlayer() {
  const { messages: m } = useLocale()
  const s = m.components.seaMusic
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [trackIndex, setTrackIndex] = useState(loadTrackIndex)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)

  const src = PLAYLIST[trackIndex]

  const syncProgress = useCallback(() => {
    const el = audioRef.current
    if (!el || !el.duration || !Number.isFinite(el.duration)) {
      setProgress(0)
      return
    }
    setProgress(el.currentTime / el.duration)
  }, [])

  const play = useCallback(async () => {
    const el = audioRef.current
    if (!el) return
    try {
      await el.play()
      setPlaying(true)
    } catch {
      setPlaying(false)
    }
  }, [])

  const pause = useCallback(() => {
    audioRef.current?.pause()
    setPlaying(false)
  }, [])

  const togglePlay = useCallback(() => {
    if (playing) pause()
    else void play()
  }, [playing, play, pause])

  const goTo = useCallback((nextIndex: number) => {
    const wrapped = (nextIndex + PLAYLIST.length) % PLAYLIST.length
    setTrackIndex(wrapped)
    saveTrackIndex(wrapped)
    setProgress(0)
  }, [])

  const prevTrack = useCallback(() => goTo(trackIndex - 1), [goTo, trackIndex])
  const nextTrack = useCallback(() => goTo(trackIndex + 1), [goTo, trackIndex])

  useEffect(() => {
    const el = audioRef.current
    if (!el) return
    setProgress(0)
    el.load()
    if (playing) {
      void el.play().catch(() => setPlaying(false))
    }
  }, [src]) // eslint-disable-line react-hooks/exhaustive-deps -- reload on track change

  useEffect(() => {
    const el = audioRef.current
    if (!el) return

    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onTimeUpdate = () => syncProgress()
    const onLoaded = () => syncProgress()
    const onEnded = () => nextTrack()

    el.addEventListener('play', onPlay)
    el.addEventListener('pause', onPause)
    el.addEventListener('timeupdate', onTimeUpdate)
    el.addEventListener('loadedmetadata', onLoaded)
    el.addEventListener('ended', onEnded)

    return () => {
      el.removeEventListener('play', onPlay)
      el.removeEventListener('pause', onPause)
      el.removeEventListener('timeupdate', onTimeUpdate)
      el.removeEventListener('loadedmetadata', onLoaded)
      el.removeEventListener('ended', onEnded)
    }
  }, [syncProgress, nextTrack])

  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden && playing) pause()
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [playing, pause])

  return (
    <div className="sea-music-player" aria-label={s.ariaLabel}>
      <audio ref={audioRef} src={src} preload="metadata" />
      <div
        className="sea-music-player-ring"
        style={{ ['--sea-music-progress' as string]: `${Math.round(progress * 100)}%` }}
        aria-hidden
      />
      <div className="sea-music-player-controls">
        <button
          type="button"
          className="sea-music-btn"
          onClick={prevTrack}
          aria-label={s.prev}
          title={s.prev}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
            <path fill="currentColor" d="M6 6h2v12H6V6zm3.5 6 8.5 6V6l-8.5 6z" />
          </svg>
        </button>
        <button
          type="button"
          className="sea-music-btn sea-music-btn--primary"
          onClick={togglePlay}
          aria-label={playing ? s.pause : s.play}
          title={playing ? s.pause : s.play}
        >
          {playing ? (
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden>
              <path fill="currentColor" d="M6 5h4v14H6V5zm8 0h4v14h-4V5z" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden>
              <path fill="currentColor" d="M8 5v14l11-7-11-7z" />
            </svg>
          )}
        </button>
        <button
          type="button"
          className="sea-music-btn"
          onClick={nextTrack}
          aria-label={s.next}
          title={s.next}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
            <path fill="currentColor" d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
