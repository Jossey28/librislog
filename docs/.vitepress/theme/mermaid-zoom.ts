export function installMermaidZoom(el: HTMLElement): void {
  if (el.dataset.mz) return
  el.dataset.mz = '1'

  const svg = el.querySelector('svg')
  if (!svg) return

  const group = document.createElement('div')
  Object.assign(group.style, {
    margin: '1em 0',
  })
  el.parentNode?.insertBefore(group, el)
  group.appendChild(el)

  const wrapper = document.createElement('div')
  Object.assign(wrapper.style, {
    overflow: 'hidden',
    cursor: 'grab',
    border: '1px solid var(--vp-c-divider)',
    borderRadius: '6px',
    position: 'relative',
    touchAction: 'none',
  })
  el.style.margin = '0'
  group.insertBefore(wrapper, el)
  wrapper.appendChild(el)
  svg.style.display = 'block'

  let scale = 1, tx = 0, ty = 0

  const set = () => {
    svg.style.transform = `translate(${tx}px,${ty}px) scale(${scale})`
    svg.style.transformOrigin = '0 0'
  }

  wrapper.addEventListener('wheel', (e) => {
    e.preventDefault()
    const rect = wrapper.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15
    const ns = Math.min(5, Math.max(0.15, scale * factor))
    tx = mx - (mx - tx) * (ns / scale)
    ty = my - (my - ty) * (ns / scale)
    scale = ns
    set()
  }, { passive: false })

  let dragging = false, sx = 0, sy = 0, px = 0, py = 0

  wrapper.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return
    dragging = true
    wrapper.style.cursor = 'grabbing'
    sx = e.clientX; sy = e.clientY
    px = tx; py = ty
    wrapper.setPointerCapture(e.pointerId)
    e.preventDefault()
  })

  wrapper.addEventListener('pointermove', (e) => {
    if (!dragging) return
    tx = px + (e.clientX - sx)
    ty = py + (e.clientY - sy)
    set()
  })

  const endDrag = () => { dragging = false; wrapper.style.cursor = 'grab' }
  wrapper.addEventListener('pointerup', endDrag)
  wrapper.addEventListener('pointercancel', endDrag)

  wrapper.addEventListener('dblclick', () => { scale = 1; tx = 0; ty = 0; set() })

  const zoom = (factor: number) => {
    const rect = wrapper.getBoundingClientRect()
    const mx = rect.width / 2
    const my = rect.height / 2
    const ns = Math.min(5, Math.max(0.15, scale * factor))
    tx = mx - (mx - tx) * (ns / scale)
    ty = my - (my - ty) * (ns / scale)
    scale = ns
    set()
  }

  const bar = document.createElement('div')
  Object.assign(bar.style, {
    display: 'flex',
    gap: '2px',
    justifyContent: 'center',
    padding: '6px 0 0 0',
  })

  const btnStyle: Record<string, string> = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    border: '1px solid var(--vp-c-divider)',
    borderRadius: '6px',
    background: 'var(--vp-c-bg)',
    color: 'var(--vp-c-text-2)',
    fontFamily: 'var(--vp-font-family-base)',
    fontSize: '16px',
    lineHeight: '1',
    cursor: 'pointer',
    userSelect: 'none',
  }

  const mkBtn = (text: string, title: string, action: () => void) => {
    const b = document.createElement('button')
    Object.assign(b.style, btnStyle)
    b.textContent = text
    b.title = title
    const restore = () => Object.assign(b.style, btnStyle)
    b.addEventListener('mouseenter', () => {
      b.style.background = 'var(--vp-c-default-soft)'
      b.style.borderColor = 'var(--vp-c-brand-1)'
      b.style.color = 'var(--vp-c-brand-1)'
    })
    b.addEventListener('mouseleave', restore)
    b.addEventListener('click', action)
    return b
  }

  const plus = mkBtn('+', 'Zoom in', () => zoom(1.3))
  const minus = mkBtn('−', 'Zoom out', () => zoom(1 / 1.3))
  const reset = mkBtn('⟲', 'Reset zoom', () => { scale = 1; tx = 0; ty = 0; set() })

  ;[minus, reset, plus].forEach(b => bar.appendChild(b))
  group.appendChild(bar)
}
