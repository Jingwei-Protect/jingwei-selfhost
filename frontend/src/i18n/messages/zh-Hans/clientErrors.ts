export const clientErrors = {
  networkFailed: '网络连接失败，请检查网络后重试。若你在本地开发，请先启动后端服务。',
  requestFailed: '请求失败 ({status})',
  apiNotFound: '接口未找到，请确认后端已启动',
  loadFileFailed: '无法加载文件',
} as const
