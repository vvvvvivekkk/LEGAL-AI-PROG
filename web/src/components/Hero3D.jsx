import { useEffect, useRef } from 'react'

// Lightweight 3D: a rotating point cloud drawn on a 2D canvas with hand-rolled
// perspective projection — no three.js dependency. Thematically it's the
// embedding space the whole product is built on. Honors reduced-motion by
// rendering a single static frame.
const REDUCED =
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// Orange ramp read from the theme tokens at mount (a canvas can't use CSS
// variables directly): far points are the pale ring orange, near points the
// strong brand orange, so depth reads as the brand gradient on white.
const RAMP_TOKENS = ['--color-brand-ring', '--color-brand', '--color-brand-strong']

function hexToRgb(hex) {
  const h = hex.trim().replace('#', '')
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16))
}

function readRamp(el) {
  const css = getComputedStyle(el)
  return RAMP_TOKENS.map((t) => hexToRgb(css.getPropertyValue(t)))
}

function brandColor(stops, t) {
  const seg = t < 0.5 ? 0 : 1
  const u = (t - seg * 0.5) * 2
  const a = stops[seg]
  const b = stops[seg + 1]
  return [0, 1, 2].map((i) => Math.round(a[i] + (b[i] - a[i]) * u))
}

function fibonacciSphere(n) {
  const pts = []
  const golden = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2
    const r = Math.sqrt(Math.max(0, 1 - y * y))
    const theta = golden * i
    pts.push([Math.cos(theta) * r, y, Math.sin(theta) * r])
  }
  return pts
}

export default function Hero3D({ count = 220 }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const points = fibonacciSphere(count)
    const stops = readRamp(canvas)
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let raf = 0
    let w = 0
    let h = 0
    let angle = 0
    // Breathing phase, independent of rotation: the sphere rotates *and*
    // swells slightly, so the motion is legible even in a still-ish glance.
    let phase = 0

    function resize() {
      const rect = canvas.getBoundingClientRect()
      w = rect.width
      h = rect.height
      canvas.width = Math.max(1, Math.floor(w * dpr))
      canvas.height = Math.max(1, Math.floor(h * dpr))
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    function draw() {
      ctx.clearRect(0, 0, w, h)
      const cx = w / 2
      const cy = h / 2
      // 3% swell either side of the base radius — enough to read as alive,
      // small enough not to wobble the hero's composition.
      const R = Math.min(w, h) * 0.36 * (1 + Math.sin(phase) * 0.03)
      const focal = 3
      const cosA = Math.cos(angle)
      const sinA = Math.sin(angle)
      const tilt = 0.42
      const cosT = Math.cos(tilt)
      const sinT = Math.sin(tilt)

      const projected = points
        .map(([x, y, z]) => {
          const rx = x * cosA + z * sinA
          const rz = -x * sinA + z * cosA
          const ty = y * cosT - rz * sinT
          const tz = y * sinT + rz * cosT
          return [rx, ty, tz]
        })
        .sort((a, b) => a[2] - b[2]) // far to near for correct layering

      for (const [x, y, z] of projected) {
        const persp = focal / (focal - z)
        const sx = cx + x * R * persp
        const sy = cy + y * R * persp
        const depth = (z + 1) / 2 // 0 (far) .. 1 (near)
        const size = (0.8 + depth * 2.4) * persp
        const [r, g, b] = brandColor(stops, depth)
        ctx.beginPath()
        // Near points brighten and dim with the same breath.
        const pulse = 0.9 + Math.sin(phase) * 0.1
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${(0.45 + depth * 0.5) * pulse})`
        ctx.arc(sx, sy, Math.max(0.4, size), 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const ro = new ResizeObserver(() => {
      resize()
      if (REDUCED) draw()
    })
    ro.observe(canvas)
    resize()

    if (REDUCED) {
      draw()
    } else {
      const loop = () => {
        angle += 0.0045
        phase += 0.012
        draw()
        raf = requestAnimationFrame(loop)
      }
      raf = requestAnimationFrame(loop)
    }

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [count])

  return <canvas ref={canvasRef} className="h-full w-full" aria-hidden="true" />
}
