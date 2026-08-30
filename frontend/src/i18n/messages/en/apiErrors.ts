export const apiErrors = {
  dispTextRequired: 'Watermark text is required when displacement watermark is enabled',
  logoFileRequired: 'Upload a logo image when the logo watermark is enabled',
  betaCodeRequired: 'A valid beta code is required',
  betaCodeInvalid: 'Invalid beta code',
  betaNotOpen: 'AI Inspect Assist beta is not open yet. Please try again later or contact support.',
  serverError: 'Server error: {detail}',
  outputFailed: 'Output failed: {detail}',
  previewFailed: 'Preview failed: {detail}',
  holoCaptureUnavailable: 'Flash-card recording is temporarily unavailable. Please try again later.',
  holoCaptureFailed: 'Flash-card recording failed: {detail}',
} as const
