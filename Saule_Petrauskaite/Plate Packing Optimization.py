import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle as PltCircle, Polygon

GAP = 2.0                
FORBIDDEN_RADIUS = 10   

def rot2d(theta):
    c = math.cos(theta)
    s = math.sin(theta)
    return np.array([[c, -s], [s, c]], dtype=np.float32)

def rect_corners(cx, cy, w, h):
    hw = w / 2
    hh = h / 2
    return np.array([
        [cx - hw, cy - hh],
        [cx + hw, cy - hh],
        [cx + hw, cy + hh],
        [cx - hw, cy + hh],
    ])

# Fixed forbidden zones
def fixed_forbidden_zones(plate_R, edge_offset_frac=0.15):
    r = (1.0 - edge_offset_frac) * plate_R
    angles = np.array([0, 2*np.pi/3, 4*np.pi/3])
    return np.column_stack((r * np.cos(angles), r * np.sin(angles)))

# Circle packing 
def pack_circles_hex(
    plate_R, r, forbidden_points,
    angle_steps=30, offset_steps=14):
    r_eff = r + GAP / 2
    dx = 2 * r_eff
    dy = math.sqrt(3) * r_eff

    xs = np.arange(-plate_R, plate_R + dx, dx, dtype=np.float32)
    ys = np.arange(-plate_R, plate_R + dy, dy, dtype=np.float32)

    rows = []
    for j, y in enumerate(ys):
        xoff = 0.0 if (j & 1) == 0 else r_eff
        rows.append(np.column_stack((xs + xoff, np.full_like(xs, y))))
    base = np.vstack(rows)

    forb = np.asarray(forbidden_points, dtype=np.float32)

    plate_r2 = (plate_R - r - GAP) ** 2
    forb_r2 = (r + FORBIDDEN_RADIUS + GAP) ** 2

    best_score = -1
    best_centers = None

    for a in range(angle_steps):
        theta = (a / angle_steps) * (math.pi / 3)
        rot = base @ rot2d(theta).T

        for oi in range(offset_steps):
            offx = (oi / offset_steps) * dx
            for oj in range(offset_steps):
                offy = (oj / offset_steps) * dy
                pts = rot + (offx, offy)

                mask = np.sum(pts**2, axis=1) <= plate_r2
                pts = pts[mask]
                if pts.size == 0:
                    continue

                if len(forb):
                    d2 = np.sum((pts[:, None, :] - forb[None, :, :])**2, axis=2)
                    pts = pts[np.all(d2 > forb_r2, axis=1)]

                if pts.shape[0] > best_score:
                    best_score = pts.shape[0]
                    best_centers = pts.copy()

    return best_centers.tolist(), best_score


# Rectangle packing
def pack_rectangles_grid(
    plate_R, w, h, forbidden_points,
    offset_steps=14):
    # orthogonal grid
    w_eff = w + GAP
    h_eff = h + GAP

    nx = int(2 * plate_R / w_eff) + 6
    ny = int(2 * plate_R / h_eff) + 6

    gx = (np.arange(nx) - nx / 2) * w_eff
    gy = (np.arange(ny) - ny / 2) * h_eff

    base = np.array([(x, y) for y in gy for x in gx], dtype=np.float32)

    forb = np.asarray(forbidden_points, dtype=np.float32)

    # Rectangle corner offsets
    cx = np.array([ w/2, -w/2,  w/2, -w/2], dtype=np.float32)
    cy = np.array([ h/2,  h/2, -h/2, -h/2], dtype=np.float32)

    plate_r2 = (plate_R - GAP) ** 2
    wx = w / 2 + FORBIDDEN_RADIUS + GAP
    hy = h / 2 + FORBIDDEN_RADIUS + GAP

    best_score = -1
    best_rects = None

    for oi in range(offset_steps):
        offx = (oi / offset_steps) * w_eff
        for oj in range(offset_steps):
            offy = (oj / offset_steps) * h_eff
            pts = base + (offx, offy)

            corners = pts[:, None, :] + np.stack((cx, cy), axis=1)
            mask = np.all(np.sum(corners**2, axis=2) <= plate_r2, axis=1)
            pts = pts[mask]
            if pts.size == 0:
                continue

            if len(forb):
                dx = np.abs(pts[:, None, 0] - forb[None, :, 0])
                dy = np.abs(pts[:, None, 1] - forb[None, :, 1])
                pts = pts[np.all((dx > wx) | (dy > hy), axis=1)]

            if pts.shape[0] > best_score:
                best_score = pts.shape[0]
                best_rects = pts.copy()

    return best_rects.tolist(), best_score

# Visualization
def plot_solution(
    plate_R, forbidden_points,
    shape_type, circles=None, rects=None,
    circle_r=None, rect_w=None, rect_h=None):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_aspect("equal")

    ax.add_patch(PltCircle((0, 0), plate_R, color="#0d5c73", alpha=0.95))

    for fx, fy in forbidden_points:
        ax.add_patch(PltCircle((fx, fy), FORBIDDEN_RADIUS, color="black"))

    if shape_type == "c":
        for cx, cy in circles:
            ax.add_patch(PltCircle((cx, cy), circle_r, color="#4caf50"))
        ax.set_title(f"Packed circles: {len(circles)}")

    else:
        for cx, cy in rects:
            ax.add_patch(Polygon(
                rect_corners(cx, cy, rect_w, rect_h),
                closed=True, color="#4caf50"
            ))
        ax.set_title(f"Packed rectangles: {len(rects)}")

    lim = plate_R * 1.1
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.grid(alpha=0.3)
    plt.show()


# Main
def main():
    print("Plate Packing Optimization")
    plate_d = float(input("Enter plate diameter: "))
    plate_R = plate_d / 2

    shape_type = input("Shape type: c or r: ").strip().lower()
    forbidden_points = fixed_forbidden_zones(plate_R)

    if shape_type == "c":
        r = float(input("Enter circle radius: "))
        circles, score = pack_circles_hex(
            plate_R, r, forbidden_points)
        print(f"Best found circle count = {score}")
        plot_solution(
            plate_R, forbidden_points,
            "c", circles=circles, circle_r=r)

    else:
        w = float(input("Enter rectangle width: "))
        h = float(input("Enter rectangle height: "))
        rects, score = pack_rectangles_grid(
            plate_R, w, h, forbidden_points)
        print(f"Best found rectangle count = {score}")
        plot_solution(
            plate_R, forbidden_points,
            "r", rects=rects, rect_w=w, rect_h=h)

if __name__ == "__main__":
    main()