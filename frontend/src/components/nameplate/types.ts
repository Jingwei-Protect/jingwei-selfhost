export type TextEffect = 'normal' | 'gold' | 'rainbow'



export type SponsorTier = 'none' | 'supporter' | 'sustained' | 'deep' | 'patron'



export type FrameStyle = 'default' | 'sustained' | 'deep' | 'patron'



export interface NameplateSaveData {

  username: string

  imageData: string

  textEffect: TextEffect

  frameStyle: FrameStyle

}



export interface NameplateEditorProps {

  initialUsername?: string

  initialEffect?: TextEffect

  initialFrameStyle?: FrameStyle

  /** 当前用户的支持等级，控制工具栏中的高级工具是否可用 */

  userTier?: SponsorTier

  onDone: (data: NameplateSaveData) => void

  onCancel?: () => void

}


