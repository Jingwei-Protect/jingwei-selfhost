export const clientErrors = {
  networkFailed: 'Network connection failed. Check your connection and try again. If developing locally, start the backend first.',
  requestFailed: 'Request failed ({status})',
  apiNotFound: 'API endpoint not found—confirm the backend is running',
  loadFileFailed: 'Could not load file',
} as const
