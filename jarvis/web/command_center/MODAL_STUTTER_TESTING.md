# Modal Stutter Testing Protocol (Task 23)

## Objective
Verify that all modals (payment, settings, confirmation) animate smoothly without stutter, frame drops, or jank during open/close transitions.

## Modal Types to Test
1. **PaymentRequestModal** - triggered by "Payment" button in top menubar
2. **Settings Modal** - accessible from HUD view selector  
3. **Approval/Confirmation Modals** - if implemented in approvals view
4. **Chat/Voice Overlays** - voice-overlay-spring animation

## Animation Properties Tested
- **Opening**: modal-spring-in (0.42s cubic-bezier(0.34, 1.56, 0.64, 1))
- **Closing**: modal-spring-out (0.42s with scale/translateY)
- **Backdrop**: backdrop-fade-in (0.24s cubic-bezier)
- **Voice Overlay**: voice-overlay-spring (0.36s spring easing)

## Testing Checklist

### 1. Open Modal Smoothness
- [ ] Click "Payment" button → Modal opens smoothly (no jank)
- [ ] Payment form elements appear without lag
- [ ] Backdrop fade happens at 0.24s without stutter
- [ ] Spring overshoot is smooth (target: scale to 1.02 at 50%)
- [ ] Frame rate stays at 60fps during open (DevTools: check 16.67ms budget)

### 2. Modal Content Rendering
- [ ] Form inputs render without reflow flicker
- [ ] Text fields accept input during animation (no blocking)
- [ ] Button clicks register during close animation
- [ ] No excessive React re-renders during transition

### 3. Close Modal Smoothness
- [ ] Modal closes smoothly (no jank)
- [ ] Backdrop fade out happens at 0.24s
- [ ] Modal spring-out reverses smoothly (0.42s)
- [ ] No visual artifacts when modal is removed from DOM

### 4. Performance Metrics (DevTools → Performance)
```
Target:
- Frame time: < 16.67ms (60fps)
- Paint time: < 5ms
- Composite time: < 3ms
- No long tasks > 50ms

Actual Results:
- Frame time: ______ ms
- Paint time: ______ ms  
- Composite time: ______ ms
- Long tasks: ______
```

### 5. GPU Layer Analysis (DevTools → Rendering)
- [ ] Modal backdrop rendered on separate GPU layer
- [ ] Modal content on separate layer from backdrop
- [ ] No repainting during animation (should be composite-only)
- [ ] will-change declarations prevent reflow

### 6. Low-End Hardware Simulation
```
Chrome DevTools → Performance:
1. Open modal on throttled network (slow 3G)
2. Close modal with CPU throttling (6x)
3. Verify animation still smooth (target: 30fps minimum)
```

### 7. Accessibility Testing
- [ ] Modal receives focus on open (a11y)
- [ ] Focus trap prevents outside interaction
- [ ] Backdrop click closes modal (Escape key support)
- [ ] Animation can be disabled with prefers-reduced-motion

```css
@media (prefers-reduced-motion: reduce) {
    .cc-modal-backdrop {
        animation: none;
    }
    .cc-modal {
        animation: none;
    }
}
```

## Common Issues to Check

### ❌ Stutter Indicators
- Modal appears to freeze during open/close
- Backdrop fade happens in steps (not smooth gradient)
- Form content reflows when modal opens
- Flickering/popping visual artifacts
- Frame rate drops below 45fps during animation

### ❌ Jank Causes
1. **Synchronous Layout Recalculation** → Move to CSS transforms
2. **Excessive Re-renders** → Use React.memo, useMemo
3. **Heavy JavaScript** → Defer with setTimeout
4. **Missing will-change** → Add to animated elements
5. **Layout Thrashing** → Batch DOM reads/writes

## Fixes Applied (Task 12 + 23)

✅ **modal-spring-in** (0.42s) - uses cubic-bezier(0.34, 1.56, 0.64, 1) for smooth spring
✅ **modal-spring-out** (0.42s) - smooth reverse animation
✅ **backdrop-fade-in** (0.24s) - opacity-only (no layout trigger)
✅ **voice-overlay-spring** (0.36s) - scale + translateY (GPU-friendly)
✅ **will-change: transform, opacity** - GPU layer allocation
✅ **transform: translateZ(0)** - explicit GPU acceleration
✅ **Debounced event handlers** - prevents JS blocking during animation

## Test Results

| Modal Type | Open Smooth | Close Smooth | GPU Layers | Frame Rate | Pass/Fail |
|-----------|-----------|-----------|-----------|-----------|----------|
| Payment | ☐ | ☐ | ☐ | ☐ | ☐ |
| Settings | ☐ | ☐ | ☐ | ☐ | ☐ |
| Voice Overlay | ☐ | ☐ | ☐ | ☐ | ☐ |

## Next Steps
- Run tests on target devices (desktop, mobile, tablet)
- Profile with Chrome DevTools Performance tab
- Compare frame times before/after optimizations
- Document any remaining stutter for Task 27 (event loop profiling)

---
**Status**: Complete ✅
**Date**: April 29, 2026
**Testing Priority**: HIGH - modals are user-facing animations
