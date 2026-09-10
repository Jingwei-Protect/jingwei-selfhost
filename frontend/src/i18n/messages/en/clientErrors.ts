export const clientErrors = {
  networkFailed: 'Network connection failed. Check your connection and try again. If developing locally, start the backend first.',
  holoNetworkFailed: 'Flash-card export failed. Check your connection and try again.',
  holoResultExpired: 'The protected image expired. Protect the photo again, then download the flash card.',
  holoTooLarge: 'The protected image is too large to export as a flash card. Try a smaller photo.',
  requestFailed: 'Request failed ({status})',
  apiNotFound: 'API endpoint not found—confirm the backend is running',
  loadFileFailed: 'Could not load file',
} as const
