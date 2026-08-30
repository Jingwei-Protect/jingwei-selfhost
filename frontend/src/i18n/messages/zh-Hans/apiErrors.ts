export const apiErrors = {
  dispTextRequired: '启用位移水印时必须填写水印文字',
  logoFileRequired: '启用 Logo 水印时必须上传图片',
  betaCodeRequired: '需要有效内测码',
  betaCodeInvalid: '内测码无效',
  betaNotOpen: '鉴AI辅助内测未开放，请稍后再试或联系管理员。',
  serverError: '服务器错误：{detail}',
  outputFailed: '输出失败：{detail}',
  previewFailed: '预览失败：{detail}',
  holoCaptureUnavailable: '闪卡录制暂时不可用，请稍后重试。',
  holoCaptureFailed: '闪卡录制失败：{detail}',
} as const
