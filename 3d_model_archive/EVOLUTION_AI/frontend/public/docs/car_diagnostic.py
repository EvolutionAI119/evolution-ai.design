"""Quick diagnostic script to preview the car model shape"""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from verify_algorithm import (
    HardpointParams, derive_hardpoints, side_upper_profile, top_width_profile,
    lerp_profile, compute_zone_weights, compute_cross_section_params,
    generate_31point_cross_section, generate_car_body, smoothstep
)

p = HardpointParams()
h = derive_hardpoints(p)

print("=" * 60)
print("  BMW 3 Series (F30) Dimension Verification")
print("=" * 60)

# Check primary parameters
checks = [
    ("Length L", p.L, 4.84, 0.05),
    ("Width W", p.W, 1.83, 0.05),
    ("Height H", p.H, 1.45, 0.05),
    ("Front Overhang FO", p.FO, 0.92, 0.05),
    ("Rear Overhang RO", p.RO, 0.96, 0.05),
    ("Wheelbase WB", p.WB, 2.96, 0.05),
    ("Track Width TW", p.TW, 1.59, 0.05),
    ("Wheel Radius WR", p.WR, 0.335, 0.01),
    ("Ground Clearance GC", p.GC, 0.14, 0.02),
    ("Waistline WL", p.WL, 0.76, 0.05),
    ("A-pillar Angle AA", p.AA, 30.0, 3.0),
    ("C-pillar Angle RA", p.RA, 38.0, 5.0),
]

print("\n--- Primary Parameters ---")
for name, val, expected, tol in checks:
    status = "PASS" if abs(val - expected) < tol else "WARN"
    print(f"  {name:25s}: {val:7.3f}  expected: {expected:7.3f}  [{status}]")

# Check secondary hardpoints
print("\n--- Secondary Hardpoints ---")
print(f"  Front wheel X (fwx):    {h.fwx:.3f}m")
print(f"  Rear wheel X (rwx):      {h.rwx:.3f}m")
print(f"  Wheel center Y (wcy):    {h.wcy:.3f}m")
print(f"  Nose tip Y:              {h.noseTipY:.3f}m  (expected: ~0.50m)")
print(f"  Hood Y:                  {h.hoodY:.3f}m  (expected: ~0.74m)")
print(f"  Waist Y:                 {h.waistY:.3f}m  (expected: ~0.90m)")
print(f"  A-pillar base X:         {h.aBaseX:.3f}m")
print(f"  A-pillar top X:          {h.aTopX:.3f}m")
print(f"  A-pillar top Y:          {h.aTopY:.3f}m  (expected: ~1.36m)")
print(f"  C-pillar base X:         {h.cBaseX:.3f}m")
print(f"  C-pillar top X:          {h.cTopX:.3f}m")
print(f"  C-pillar top Y:          {h.cTopY:.3f}m  (expected: ~1.33m)")
print(f"  Roof peak X:             {h.roofPeakX:.3f}m")
print(f"  Roof Y:                  {h.roofY:.3f}m  (expected: ~1.45m)")

# Check L = FO + WB + RO
total = p.FO + p.WB + p.RO
print(f"\n  FO+WB+RO = {total:.3f}m  L = {p.L:.3f}m  match: {abs(total - p.L) < 0.01}")

# Check side profile key points
sup = side_upper_profile(p, h)
print("\n--- Side Profile Key Points ---")
for i, (x, y) in enumerate(sup):
    print(f"  Pt {i:2d}: x={x:.3f}m  y={y:.3f}m")

# Check top width profile key points
twp = top_width_profile(p)
hw = p.W / 2
print("\n--- Top Width Profile Key Points ---")
for i, (x, w) in enumerate(twp):
    print(f"  Pt {i:2d}: x={x:.3f}m  hw={w:.3f}m  ({w/hw*100:.1f}% of max)")

# Check cross-section at cabin midpoint
x_cabin = (h.aTopX + h.cTopX) / 2
topY = lerp_profile(sup, x_cabin)
hw_val = lerp_profile(twp, x_cabin)
ho, co, to = compute_zone_weights(x_cabin, h)
tumble_rad = p.CA * math.pi / 180
shldHW, roofHW = compute_cross_section_params(hw_val, p.shoulderW, tumble_rad, ho, co, to)

print(f"\n--- Cabin Cross-Section at x={x_cabin:.3f}m ---")
print(f"  Half-width (hw):         {hw_val:.3f}m  ({hw_val/hw*100:.1f}% of max)")
print(f"  Shoulder half-width:      {shldHW:.3f}m  ({shldHW/hw*100:.1f}% of max)")
print(f"  Roof half-width:         {roofHW:.3f}m  ({roofHW/hw*100:.1f}% of max)")
print(f"  Tumblehome angle:        {p.CA:.1f}°")
print(f"  Expected roof width:      ~65-75% of max")
print(f"  Actual roof width:       {roofHW/hw*100:.1f}% of max")

# Generate preview figure
fig, axes = plt.subplots(2, 2, figsize=(16, 10))

# 1. Side profile
ax = axes[0][0]
sx = [pt[0] for pt in sup]
sy = [pt[1] for pt in sup]
ax.plot(sx, sy, 'b-o', markersize=5, linewidth=2, label='Upper profile')
ax.plot([0, p.L], [p.GC, p.GC], 'k-', linewidth=1, label='Ground')
ax.plot([0, p.L], [0, 0], 'k--', linewidth=0.5, alpha=0.3)
for wx in [h.fwx, h.rwx]:
    circle = plt.Circle((wx, h.wcy), p.WR, fill=False, color='gray', linewidth=2)
    ax.add_patch(circle)
ax.plot(h.aBaseX, h.waistY, 'r^', markersize=10)
ax.plot(h.aTopX, h.aTopY, 'rv', markersize=10)
ax.plot(h.cBaseX, h.cBaseY, 'g^', markersize=10)
ax.plot(h.cTopX, h.cTopY, 'gv', markersize=10)
ax.plot(h.roofPeakX, h.roofY, 'm*', markersize=12)
ax.set_xlabel('X (m)')
ax.set_ylabel('Y (m)')
ax.set_title('Side Profile (BMW 3 Series Based)')
ax.set_aspect('equal')
ax.grid(True, alpha=0.3)
ax.legend()

# 2. Top width profile
ax = axes[0][1]
tx = [pt[0] for pt in twp]
tw = [pt[1] for pt in twp]
ax.plot(tx, tw, 'r-o', markersize=5, linewidth=2, label='Half-width')
ax.fill_between(tx, 0, tw, alpha=0.15, color='red')
ax.axhline(y=hw, color='gray', linestyle='--', alpha=0.5, label=f'Max HW={hw:.3f}m')
ax.set_xlabel('X (m)')
ax.set_ylabel('Half Width (m)')
ax.set_title('Top Width Profile')
ax.grid(True, alpha=0.3)
ax.legend()

# 3. Cross-sections at 3 locations
ax = axes[1][0]
section_positions = [
    (p.FO * 0.5, 'Hood', 'blue', '-'),
    (x_cabin, 'Cabin', 'green', ':'),
    (p.L - p.RO * 0.5, 'Trunk', 'orange', '--'),
]
for x_pos, label, color, ls in section_positions:
    topY = lerp_profile(sup, x_pos)
    hw_val = lerp_profile(twp, x_pos)
    ho, co, to = compute_zone_weights(x_pos, h)
    botY = p.GC + p.H * 0.02
    sillY = p.GC + p.WR * 0.35
    shoulderY = (topY - (topY - h.waistY) * 0.05) * ho + \
                (h.waistY + (topY - h.waistY) * 0.30) * co + \
                (topY - (topY - h.waistY) * 0.08) * to
    botHW = (hw_val * 0.62) * ho + (hw_val * 0.55) * co + (hw_val * 0.60) * to
    sillHW = (hw_val * 0.90) * ho + (hw_val * 0.82) * co + (hw_val * 0.88) * to
    waistHW = hw_val
    shldHW, roofHW = compute_cross_section_params(hw_val, p.shoulderW, tumble_rad, ho, co, to)
    kp = generate_31point_cross_section(botY, sillY, h.waistY, shoulderY, topY,
                                         botHW, sillHW, waistHW, shldHW, roofHW, hw_val)
    cz = [pt[1] for pt in kp]
    cy = [pt[0] for pt in kp]
    ax.plot(cz, cy, ls, color=color, linewidth=2, label=f'{label} (x={x_pos:.2f}m)')

ax.set_xlabel('Z (m)')
ax.set_ylabel('Y (m)')
ax.set_title('Cross-Sections at Three Zones')
ax.set_aspect('equal')
ax.grid(True, alpha=0.3)
ax.legend()

# 4. 3D surface
ax = fig.add_subplot(2, 2, 4, projection='3d')
nS_vis, nC_vis = 40, 32
verts_vis, _, _ = generate_car_body(p, nS=nS_vis, nC=nC_vis)
X = verts_vis[:, 0].reshape(nS_vis + 1, nC_vis + 1)
Y = verts_vis[:, 1].reshape(nS_vis + 1, nC_vis + 1)
Z = verts_vis[:, 2].reshape(nS_vis + 1, nC_vis + 1)
ax.plot_surface(X, Z, Y, alpha=0.8, color='steelblue', edgecolor='navy',
                linewidth=0.3, rstride=2, cstride=2, shade=True)
for wx in [h.fwx, h.rwx]:
    for wz in [p.TW / 2, -p.TW / 2]:
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(-0.10, 0.10, 4)
        cx = wx + 0.10 * np.outer(np.cos(u), np.ones(len(v)))
        cy = h.wcy + p.WR * np.outer(np.sin(u), np.ones(len(v)))
        cz = wz + 0.10 * np.outer(np.ones(len(u)), v)
        ax.plot_surface(cx, cz, cy, color='gray', alpha=0.7)
ax.set_xlabel('X (m)')
ax.set_ylabel('Z (m)')
ax.set_zlabel('Y (m)')
ax.set_title('3D Surface Preview')
ax.view_init(elev=20, azim=-50)

plt.tight_layout()
plt.savefig('car_diagnostic.png', dpi=150)
print("\nDiagnostic preview saved to: car_diagnostic.png")
