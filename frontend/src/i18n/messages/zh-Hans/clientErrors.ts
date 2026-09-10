export const clientErrors = {
  networkFailed: '网络连接失败，请检查网络后重试。若你在本地开发，请先启动后端服务。',
  holoNetworkFailed: '闪卡导出失败，请检查网络后重试。',
  holoResultExpired: '成品图已失效，请重新保护后再下载闪卡。',
  holoTooLarge: '成品图过大，请换一张较小的图后再试。',
  requestFailed: '请求失败 ({status})',
  apiNotFound: '接口未找到，请确认后端已启动',
  loadFileFailed: '无法加载文件',
} as const
