/**
 * 署名·快速 layer switch.
 * Run: npx tsx src/lib/creditVisibleLayers.test.ts
 */
import assert from 'node:assert/strict'
import {
  CREDIT_DISP_FONT_RATIO,
  CREDIT_DISP_SHADOW_STRENGTH,
  CREDIT_DISP_SHIFT,
  creditUsesAscii,
  nextCreditVisibleLayers,
  creditDispPinFromHint,
} from './creditVisibleLayers.ts'

assert.equal(creditUsesAscii('ascii', 'rich'), true)
assert.equal(creditUsesAscii('auto', 'flat'), true)
assert.equal(creditUsesAscii('auto', 'mixed'), false)
assert.equal(creditUsesAscii('auto', 'rich'), false)
assert.equal(creditUsesAscii('auto', null), false)
assert.equal(creditUsesAscii('displacement', 'flat'), false)

const dogAuto = nextCreditVisibleLayers('auto', 'rich')
assert.equal(dogAuto.asciiEnabled, false)
assert.equal(dogAuto.dispEnabled, true)
assert.equal(dogAuto.dispFontRatio, CREDIT_DISP_FONT_RATIO)
assert.equal(dogAuto.dispShift, CREDIT_DISP_SHIFT)
assert.equal(dogAuto.dispShadowStrength, CREDIT_DISP_SHADOW_STRENGTH)

const dogMixed = nextCreditVisibleLayers('auto', 'mixed')
assert.equal(dogMixed.asciiEnabled, false)
assert.equal(dogMixed.dispEnabled, true)

const leftoverThenDisplacement = nextCreditVisibleLayers('displacement', 'flat')
assert.equal(leftoverThenDisplacement.asciiEnabled, false)
assert.equal(leftoverThenDisplacement.dispEnabled, true)
assert.equal(leftoverThenDisplacement.dispFontRatio, 0.07)

const catAuto = nextCreditVisibleLayers('auto', 'flat')
assert.equal(catAuto.asciiEnabled, true)
assert.equal(catAuto.dispEnabled, false)

const beforeHint = nextCreditVisibleLayers('auto', null)
assert.equal(beforeHint.asciiEnabled, false)
assert.equal(beforeHint.dispEnabled, true)
assert.equal(beforeHint.dispFontRatio, CREDIT_DISP_FONT_RATIO)

const fallbackPin = creditDispPinFromHint(null)
assert.equal(fallbackPin.x, 0.5)
assert.equal(fallbackPin.y, 0.5)

const hostPin = creditDispPinFromHint({
  credit_disp_x: 0.48,
  credit_disp_y: 0.71,
  credit_disp_w: 0.22,
  credit_disp_h: 0.08,
})
assert.equal(hostPin.x, 0.48)
assert.equal(hostPin.y, 0.71)
assert.equal(hostPin.w, 0.22)
assert.equal(hostPin.h, 0.08)

console.log('creditVisibleLayers.test.ts ok')
