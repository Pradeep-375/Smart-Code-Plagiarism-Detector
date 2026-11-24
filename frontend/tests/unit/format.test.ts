import { describe, expect, it } from 'vitest'
import { bytes, heatColor, pct, riskTone, timeAgo } from '../../src/utils/format'

describe('format utils', () => {
  it('formats percentages and missing values', () => {
    expect(pct(0.756)).toBe('76%')
    expect(pct(0.756, 1)).toBe('75.6%')
    expect(pct(null)).toBe('—')
  })
  it('formats byte sizes', () => {
    expect(bytes(512)).toBe('512 B')
    expect(bytes(2048)).toBe('2.0 KB')
    expect(bytes(5 * 1048576)).toBe('5.0 MB')
  })
  it('maps risk to a tone', () => {
    expect(riskTone('high')).toBe('red')
    expect(riskTone('medium')).toBe('amber')
    expect(riskTone('low')).toBe('green')
  })
  it('clamps heat colours', () => {
    expect(heatColor(-1)).toBe(heatColor(0))
    expect(heatColor(5)).toBe(heatColor(1))
  })
  it('renders relative time', () => {
    expect(timeAgo(new Date().toISOString())).toBe('just now')
    expect(timeAgo(new Date(Date.now() - 3 * 3600 * 1000).toISOString())).toBe('3h ago')
  })
})
