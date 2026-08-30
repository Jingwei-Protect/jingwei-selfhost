import { useState } from 'react'
import WigglyDefs from './WigglyDefs'
import NameplateTopBar from './NameplateTopBar'
import NameplateToolbar from './NameplateToolbar'
import NameplateCanvasFrame from './NameplateCanvasFrame'
import NameplatePalette from './NameplatePalette'
import NameplateBottomBar from './NameplateBottomBar'
import NameplateFramePicker from './NameplateFramePicker'
import { useNameplateCanvas } from './useNameplateCanvas'
import { TOOLS, UPLOAD_IMAGE_MAX_BYTES } from './constants'
import { isFrameStyleUnlocked } from './frameStyles'
import type { NameplateEditorProps, TextEffect, FrameStyle } from './types'
import { useLocale } from '../../i18n/LocaleContext'

export type { NameplateSaveData, TextEffect, NameplateEditorProps, FrameStyle } from './types'
export { CANVAS_W, CANVAS_H, PALETTE } from './constants'

export default function NameplateEditor({
  initialUsername = '',
  initialEffect = 'rainbow',
  initialFrameStyle = 'default',
  userTier = 'supporter',
  onDone,
  onCancel,
}: NameplateEditorProps) {
  const { messages: m } = useLocale()
  const t = m.components.nameplate
  const [username, setUsername] = useState(initialUsername)
  const [textEffect, setTextEffect] = useState<TextEffect>(initialEffect)
  const [frameStyle, setFrameStyle] = useState<FrameStyle>(
    isFrameStyleUnlocked(userTier, initialFrameStyle) ? initialFrameStyle : 'default',
  )
  const [showEffectPreview, setShowEffectPreview] = useState(true)
  const [uploadError, setUploadError] = useState('')

  const canvas = useNameplateCanvas()

  const handleUploadImage = async (file: File) => {
    setUploadError('')
    try {
      await canvas.importImageFromFile(file)
    } catch (err) {
      const code = err instanceof Error ? err.message : 'failed'
      if (code === 'too_large') {
        setUploadError(t.uploadImageTooLarge.replace('{kb}', String(Math.round(UPLOAD_IMAGE_MAX_BYTES / 1024))))
      } else {
        setUploadError(t.uploadImageFailed)
      }
    }
  }

  const handleSave = () => {
    const name = username.trim() || t.anonymousSupporter
    onDone({
      username: name,
      imageData: canvas.exportImage(),
      textEffect,
      frameStyle,
    })
  }

  const activeTool = TOOLS.find(t => t.id === canvas.tool)
  const toolLabel = activeTool?.title ?? t.defaultToolLabel

  return (
    <div className="np-editor">
      <WigglyDefs />

      <NameplateTopBar
        username={username}
        onUsernameChange={setUsername}
        textEffect={textEffect}
        onTextEffectChange={setTextEffect}
        showEffectPreview={showEffectPreview}
        onToggleEffectPreview={() => setShowEffectPreview(v => !v)}
        onSave={handleSave}
        onClear={canvas.clearCanvas}
        onUploadImage={handleUploadImage}
        userTier={userTier}
      />

      {uploadError && (
        <p className="np-upload-error" role="alert">{uploadError}</p>
      )}

      <p className="np-canvas-size-hint text-sm text-secondary">{t.canvasSizeHint}</p>

      <NameplateFramePicker
        value={frameStyle}
        onChange={setFrameStyle}
        userTier={userTier}
      />

      <div className="np-workspace">
        <NameplateToolbar
          tool={canvas.tool}
          onToolChange={canvas.setTool}
          canUndo={canvas.canUndo}
          canRedo={canvas.canRedo}
          onUndo={canvas.undo}
          onRedo={canvas.redo}
          userTier={userTier}
        />

        <NameplateCanvasFrame
          frameStyle={frameStyle}
          canvasRef={canvas.canvasRef}
          cursor={canvas.cursorForTool}
          onPointerDown={canvas.onPointerDown}
          onPointerMove={canvas.onPointerMove}
          onPointerUp={canvas.onPointerUp}
        />

        <NameplatePalette
          color={canvas.color}
          onColorChange={canvas.setColor}
          brushSize={canvas.brushSize}
          onBrushSizeChange={canvas.setBrushSize}
          brushOpacity={canvas.brushOpacity}
          onBrushOpacityChange={canvas.setBrushOpacity}
        />
      </div>

      <NameplateBottomBar
        brushSize={canvas.brushSize}
        toolLabel={toolLabel}
        onCancel={onCancel}
        onSave={handleSave}
      />
    </div>
  )
}
