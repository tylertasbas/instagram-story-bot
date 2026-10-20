"""Uçaklar yıldırım çarptığında neden düşmez? (Faraday kafesi) — 9:16 minimal çizim videosu.

Stil ve yardımcılar ../suleymaniye/render.py ile ortak.

Kullanım:
  python3 render.py              -> faraday.mp4
  python3 render.py --still 12.5 -> tek kare PNG (önizleme)
"""
import importlib.util
import math
import os
import random
import subprocess
import sys

import cairo

_spec = importlib.util.spec_from_file_location(
    "base", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "suleymaniye", "render.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

from_base = ("W H FPS clamp seg eio eo lerp mix window rgba glow_dot glow_stroke font text_c "
             "draw_dots draw_grid draw_person catmull WHITE GREY DARK ORANGE YELLOW RED SOOT WATERMARK").split()
globals().update({k: getattr(base, k) for k in from_base})

DUR = 43.0
BOLT = (1.0, 0.93, 0.45)


# ------------------------------------------------------------------ altyazılar
def T(s):
    out = []
    for w in s.split(" "):
        st = "n"
        if w.startswith("*"):
            st, w = "b", w[1:]
        elif w.startswith("^"):
            st, w = "o", w[1:]
        out.append((w, st))
    return out


base.CAPS = [
    (0.10, 1.95, T("Her yolcu uçağına yılda ortalama *1 *kez *yıldırım çarpar."), 0.07, 46),
    (2.00, 4.15, T("Ama sen *kahveni *dökmeden içmeye devam edersin. ^Nasıl?"), 0.075, 46),
    (4.40, 7.40, T("10 km yükseklik. Kabinde *180 *yolcu."), 0.11, 44),
    (7.50, 10.9, T("Ve önlerinde *bir *fırtına *bulutu."), 0.11, 44),
    (11.1, 14.6, T("Yıldırım genelde *burna ya da *kanat *ucuna çarpar."), 0.10, 44),
    (14.7, 18.8, T("Ortalama *30.000 *amper. Bu akım nereye gider?"), 0.10, 44),
    (19.0, 22.4, T("İçeri girmez. *Dış *kabuğun üzerinden akar."), 0.10, 44),
    (22.5, 25.6, T("Alüminyum gövde ya da kompozitteki *metal *ağ..."), 0.10, 44),
    (25.7, 28.6, T("...akımı *kuyruktan boşluğa geri gönderir."), 0.10, 44),
    (28.8, 31.6, T("Buna ^Faraday ^kafesi denir."), 0.12, 50),
    (31.7, 34.6, T("Yük *dış *yüzeyde akar. İçeride alan: *sıfır."), 0.10, 44),
    (34.8, 36.8, T("Korku değil, ^fizik."), 0.16, 60),
    (36.9, 38.8, T("Her uçak *yıldırım *testinden geçmeden uçamaz."), 0.09, 44),
    (39.0, 43.2, T("*Kaydet, uçmaktan korkan birine *gönder."), 0.10, 46),
]


# ------------------------------------------------------------------ geometri
def smooth(pts, n=160):
    p3 = [(x, y, 0) for x, y in pts]
    return [(x, y) for x, y, _ in catmull(p3, n)]


def ellipse_pts(cx, cy, rx, ry, n=48, a0=0.0, a1=2 * math.pi):
    return [(cx + rx * math.cos(lerp(a0, a1, k / n)), cy + ry * math.sin(lerp(a0, a1, k / n))) for k in range(n + 1)]


TOP = smooth([(70, 915), (85, 872), (130, 842), (210, 830), (500, 830), (800, 830), (905, 826), (990, 800)])
BOT = smooth([(70, 915), (90, 950), (150, 970), (230, 972), (500, 972), (700, 972), (810, 962), (930, 905), (990, 808)])
FIN = [(790, 830), (925, 640), (985, 640), (995, 802)]
TAILCAP = [(990, 800), (996, 804), (990, 808)]
STAB = [(880, 842), (1000, 818), (1006, 828), (895, 854), (880, 842)]
WING = [(420, 968), (590, 968), (770, 1062), (722, 1066), (420, 968)]
ENGINE = ellipse_pts(520, 1012, 62, 22)
INTAKE = ellipse_pts(458, 1012, 7, 22)
COCKPIT = [(98, 868), (122, 854), (152, 849)]
FLOOR = [(120, 955), (830, 955)]
RINGS = [ellipse_pts(x, 901, 15, 71) for x in range(260, 800, 100)]

PARTS = [(TOP, 1.9), (BOT, 1.9), (TAILCAP, 1.9), (FIN, 1.9), (STAB, 1.6), (WING, 1.9), (ENGINE, 1.6),
         (INTAKE, 1.2), (COCKPIT, 1.6)] + [(r, 1.0) for r in RINGS] + [(FLOOR, 1.0)]

# akım yolları (kabuğun hemen dışında)
FLOW_TOP = [(x, y - 5) for x, y in TOP]
FLOW_BOT = [(x, y + 5) for x, y in BOT]
FLOW_WING = [(x, y + 5) for x, y in BOT if x <= 420] + [(420, 974)] + \
    [(lerp(420, 722, k / 30), lerp(974, 1072, k / 30)) for k in range(31)]
FLOW_FIN = [(x, y - 5) for x, y in TOP if x <= 790] + [(lerp(790, 925, k / 20) - 4, lerp(830, 640, k / 20) - 3) for k in range(21)] + \
    [(lerp(925, 985, k / 10), 636) for k in range(11)] + [(lerp(985, 999, k / 20) + 4, lerp(636, 802, k / 20)) for k in range(21)]

SEATS = list(range(200, 790, 42))
COFFEE_X = SEATS[7]


def partial(ctx, pts, r):
    n = len(pts) - 1
    upto = clamp(r) * n
    k = int(upto)
    ctx.move_to(*pts[0])
    for p in pts[1:k + 1]:
        ctx.line_to(*p)
    if k < n:
        (x0, y0), (x1, y1) = pts[k], pts[k + 1]
        f = upto - k
        ctx.line_to(lerp(x0, x1, f), lerp(y0, y1, f))


def draw_plane(ctx, t, a, t0=None, dur=3.5, people=True):
    if a <= 0:
        return
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for i, (pts, w) in enumerate(PARTS):
        r = 1.0 if t0 is None else eo(seg(t, t0 + i * dur / len(PARTS) * 0.7, t0 + i * dur / len(PARTS) * 0.7 + 1.0))
        if r <= 0:
            continue
        faint = w <= 1.0
        partial(ctx, pts, r)
        ctx.set_line_width(w * 3)
        rgba(ctx, WHITE, a * 0.06)
        ctx.stroke()
        partial(ctx, pts, r)
        ctx.set_line_width(w)
        rgba(ctx, WHITE, a * (0.22 if faint else 0.9))
        ctx.stroke()
    if not people:
        return
    # yolcular
    for i, x in enumerate(SEATS):
        pa = a * (1 if t0 is None else eo(seg(t, t0 + 1.8 + i * 0.06, t0 + 2.2 + i * 0.06)))
        if pa <= 0:
            continue
        hl = x == COFFEE_X
        c = WHITE
        rgba(ctx, GREY, pa * 0.5)
        ctx.set_line_width(2.5)
        ctx.move_to(x - 12, 872)
        ctx.line_to(x - 7, 953)
        ctx.line_to(x + 24, 953)
        ctx.stroke()
        rgba(ctx, c, pa * (1 if hl else 0.8))
        ctx.arc(x, 878, 9, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_line_width(7)
        ctx.move_to(x, 893)
        ctx.line_to(x + 2, 925)
        ctx.line_to(x + 20, 927)
        ctx.stroke()
        ctx.set_line_width(4.5)
        ctx.move_to(x + 20, 927)
        ctx.line_to(x + 21, 953)
        ctx.stroke()
        if hl:
            # kahve fincanı
            ctx.set_line_width(3)
            ctx.move_to(x + 3, 900)
            ctx.line_to(x + 16, 892)
            ctx.stroke()
            rgba(ctx, ORANGE, pa)
            ctx.rectangle(x + 15, 880, 11, 12)
            ctx.fill()
            for k in range(2):
                ctx.move_to(x + 18 + k * 5, 876)
                for q in range(1, 8):
                    ctx.line_to(x + 18 + k * 5 + 2.5 * math.sin(q + t * 4 + k), 876 - q * 3)
                ctx.set_line_width(1.2)
                rgba(ctx, WHITE, pa * 0.45)
                ctx.stroke()


def draw_cloud(ctx, cx, cy, s, a):
    bumps = [(-1.0, 0.15, 0.45), (-0.45, -0.25, 0.6), (0.2, -0.35, 0.7), (0.8, -0.05, 0.5), (1.2, 0.2, 0.35)]
    ctx.new_path()
    for bx, by, br in bumps:
        ctx.new_sub_path()
        ctx.arc(cx + bx * s, cy + by * s, br * s, math.pi * 0.95, math.pi * 2.05)
    ctx.move_to(cx - 1.45 * s, cy + 0.3 * s)
    ctx.line_to(cx + 1.55 * s, cy + 0.3 * s)
    ctx.set_line_width(2)
    rgba(ctx, GREY, a)
    ctx.stroke()


def bolt_pts(p0, p1, seed, disp=70, depth=6):
    rnd = random.Random(seed)
    pts = [p0, p1]
    d = disp
    for _ in range(depth):
        new = [pts[0]]
        for i in range(1, len(pts)):
            (x0, y0), (x1, y1) = pts[i - 1], pts[i]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            L = math.hypot(x1 - x0, y1 - y0) or 1
            nx, ny = -(y1 - y0) / L, (x1 - x0) / L
            o = rnd.uniform(-d, d)
            new += [(mx + nx * o, my + ny * o), (x1, y1)]
        pts = new
        d *= 0.52
    return pts


def draw_bolt(ctx, p0, p1, t, a, grow=1.0, seed=0, width=4.0, branches=2):
    if a <= 0 or grow <= 0:
        return
    sd = seed * 1000 + int(t * 12)  # titreşim: ~12 Hz yeniden şekil
    pts = bolt_pts(p0, p1, sd)
    fl = 0.7 + 0.3 * random.Random(sd).random()

    def main():
        partial(ctx, pts, grow)

    glow_stroke(ctx, main, BOLT, width, a * fl, glow=1.6)
    rnd = random.Random(sd + 7)
    for b in range(branches):
        i = rnd.randint(len(pts) // 5, len(pts) * 3 // 5)
        if i / len(pts) > grow:
            continue
        x, y = pts[i]
        ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) + rnd.choice((-1, 1)) * rnd.uniform(0.5, 1.0)
        L = rnd.uniform(60, 130)
        bp = bolt_pts((x, y), (x + L * math.cos(ang), y + L * math.sin(ang)), sd + b * 31, disp=25, depth=4)

        def br(bp=bp):
            partial(ctx, bp, 1)

        glow_stroke(ctx, br, BOLT, width * 0.45, a * fl * 0.7, glow=0.8)


def draw_current(ctx, t, path, rev, a, phase=0.0):
    if a <= 0 or rev <= 0:
        return

    def p():
        partial(ctx, path, rev)

    glow_stroke(ctx, p, YELLOW, 2.6, a * 0.85, glow=1.2)
    n = len(path) - 1
    kmax = int(rev * n)
    for j in range(6):
        u = (t * 0.55 + j / 6 + phase) % 1
        k = int(u * n)
        if k < 8 or k > kmax:
            continue
        tail = path[k - 8:k + 1]

        def s(tail=tail):
            ctx.move_to(*tail[0])
            for q in tail[1:]:
                ctx.line_to(*q)

        glow_stroke(ctx, s, mix(BOLT, WHITE, 0.4), 4.0, a, glow=1.4)


def flash(ctx, t, times, a=0.22):
    v = 0.0
    for t0 in times:
        if t >= t0:
            v = max(v, math.exp(-(t - t0) * 9))
    if v > 0.01:
        rgba(ctx, (0.9, 0.92, 1.0), v * a)
        ctx.paint()


# ------------------------------------------------------------------ sahneler
CLOUD_TIP = (300, 520)
NOSE = (70, 915)
TAIL = (997, 804)


def draw_clouds(ctx, t, a):
    if a <= 0:
        return
    for i, (x0, y, s, sp) in enumerate(((900, 600, 60, 40), (300, 1180, 45, 55), (1200, 1110, 35, 70), (650, 560, 30, 30))):
        x = (x0 - t * sp) % 1500 - 200
        draw_cloud(ctx, x, y, s, a * 0.35)


def storm_cloud(ctx, t, a):
    if a <= 0:
        return
    draw_cloud(ctx, 300, 470, 110, a * 1.6)
    draw_cloud(ctx, 160, 500, 70, a * 1.2)


def scene_plane(ctx, t, a):
    if a <= 0:
        return
    ctx.save()
    ctx.translate(0, 40)
    draw_clouds(ctx, t, a)
    storm = window(t, 7.6, 28.8, 0.8) + window(t, 34.6, 39.2, 0.5)
    storm_cloud(ctx, t, a * storm)
    draw_plane(ctx, t, a, t0=4.3 if t < 12 else None)

    # 1. çarpma (burun)
    if 11.4 < t < 14.3:
        grow = eo(seg(t, 11.5, 11.85))
        ba = a * (1 - eio(seg(t, 13.6, 14.2)))
        draw_bolt(ctx, CLOUD_TIP, NOSE, t, ba, grow, seed=1)
        if grow >= 1:
            glow_dot(ctx, *NOSE, 9, BOLT, ba)
    # kanat ucu alternatifi (gösterim)
    if 13.0 < t < 14.6:
        wa = a * window(t, 13.0, 14.6, 0.25)
        glow_dot(ctx, 746, 1064, 7, BOLT, wa * (0.6 + 0.4 * math.sin(t * 20)))
        text_c(ctx, "kanat ucu", 746, 1112, 24, BOLT, wa)
        glow_dot(ctx, *NOSE, 7, BOLT, wa * (0.6 + 0.4 * math.sin(t * 20 + 1)))
        text_c(ctx, "burun", NOSE[0] + 20, NOSE[1] + 80, 24, BOLT, wa)
    # 30.000 A göstergesi
    if 14.7 < t < 18.9:
        ia = a * window(t, 14.7, 18.9, 0.3)
        n = int(30000 * eo(seg(t, 14.9, 16.2)))
        text_c(ctx, f"{n:,}".replace(",", "."), 540, 700, 110, BOLT, ia, "t")
        text_c(ctx, "amper", 540, 745, 28, GREY, ia)

    # 2. çarpma + kabuk akımı
    loop = t >= 34.6
    if 18.9 < t < 28.8 or loop:
        if loop:
            la = a
            grow, rev, rev_w, rev_f, exit_g = 1, 1, 1, 1, 1
        else:
            la = a * (1 - eio(seg(t, 28.0, 28.8)))
            grow = eo(seg(t, 19.0, 19.3))
            rev = eio(seg(t, 19.6, 22.0))
            rev_w = eio(seg(t, 20.2, 21.8))
            rev_f = eio(seg(t, 20.4, 22.4))
            exit_g = eo(seg(t, 22.4, 22.8))
        draw_bolt(ctx, CLOUD_TIP, NOSE, t, la * 0.9, grow, seed=2)
        glow_dot(ctx, *NOSE, 9, BOLT, la * grow)
        for path, r, ph in ((FLOW_TOP, rev, 0), (FLOW_BOT, rev, 0.3), (FLOW_WING, rev_w, 0.6), (FLOW_FIN, rev_f, 0.15)):
            draw_current(ctx, t, path, r, la, ph)
        draw_bolt(ctx, TAIL, (1130, 1260), t, la * 0.9, exit_g, seed=3, width=3.2)
        draw_bolt(ctx, (744, 1070), (820, 1250), t, la * 0.6, exit_g, seed=4, width=2.2, branches=0)
        # kabin içi göstergesi
        ka = la * eo(seg(t, 22.0, 22.6)) if not loop else la
        if ka > 0:
            rgba(ctx, ORANGE, ka)
            ctx.set_line_width(1.5)
            ctx.move_to(COFFEE_X + 20, 868)
            ctx.line_to(COFFEE_X + 60, 760)
            ctx.line_to(COFFEE_X + 100, 760)
            ctx.stroke()
            font(ctx, 30, "b")
            ctx.move_to(COFFEE_X + 110, 770)
            ctx.show_text("kabin içi: 0 A")
    ctx.restore()
    flash(ctx, t, [11.85, 12.5, 19.3, 22.8])


# ---- kanca
def draw_cup(ctx, t, a):
    cx = 540
    ctx.set_line_width(3)
    rgba(ctx, WHITE, a)
    ctx.move_to(420, 900)
    ctx.line_to(440, 1070)
    ctx.curve_to(450, 1100, 630, 1100, 640, 1070)
    ctx.line_to(660, 900)
    ctx.stroke()
    ctx.new_sub_path()
    ctx.arc(678, 975, 48, -math.pi / 2, math.pi / 2)
    ctx.stroke()
    ctx.save()
    ctx.translate(cx, 1112)
    ctx.scale(1, 0.12)
    ctx.arc(0, 0, 200, 0, 2 * math.pi)
    ctx.restore()
    ctx.stroke()
    # kahve yüzeyi (sabit)
    wob = 1.5 * math.sin(t * 6)
    ctx.save()
    ctx.translate(cx, 915 + wob)
    ctx.scale(1, 0.13)
    ctx.arc(0, 0, 116, 0, 2 * math.pi)
    ctx.restore()
    rgba(ctx, ORANGE, a)
    ctx.stroke()
    ctx.save()
    ctx.translate(cx, 900)
    ctx.scale(1, 0.13)
    ctx.arc(0, 0, 120, 0, 2 * math.pi)
    ctx.restore()
    rgba(ctx, WHITE, a)
    ctx.stroke()
    for k in range(3):
        x = cx - 50 + k * 50
        ctx.move_to(x, 880)
        for q in range(1, 20):
            ctx.line_to(x + 12 * math.sin(q * 0.5 + t * 3 + k * 2), 880 - q * 8)
        ctx.set_line_width(2)
        rgba(ctx, GREY, a * 0.5)
        ctx.stroke()


def scene_hook(ctx, t, a):
    if a <= 0:
        return
    a1 = a * (1 - eio(seg(t, 1.8, 2.1)))
    if a1 > 0:
        text_c(ctx, "1", 540, 760, 200, WHITE, a1 * eo(seg(t, 0.1, 0.4)), "t")
        text_c(ctx, "yıldırım / yıl", 540, 815, 30, GREY, a1 * eo(seg(t, 0.2, 0.5)))
        ctx.save()
        ctx.translate(540, 1080)
        ctx.scale(0.55, 0.55)
        ctx.translate(-540, -900)
        draw_plane(ctx, t, a1, people=False)
        if t > 0.5:
            draw_bolt(ctx, (250, 420), NOSE, t, a1 * (1 - seg(t, 1.0, 1.6)) * 1.0, eo(seg(t, 0.5, 0.65)), seed=9, width=6)
        ctx.restore()
    a2 = a * eo(seg(t, 1.95, 2.3))
    if a2 > 0:
        # uçak penceresi ve dışarıda şimşek
        ctx.save()
        ctx.new_path()
        x0, y0, w, h, r = 440, 520, 200, 280, 90
        ctx.arc(x0 + r + 10, y0 + r, r, math.pi, 1.5 * math.pi)
        ctx.arc(x0 + w - r - 10, y0 + r, r, 1.5 * math.pi, 2 * math.pi)
        ctx.arc(x0 + w - r - 10, y0 + h - r, r, 0, 0.5 * math.pi)
        ctx.arc(x0 + r + 10, y0 + h - r, r, 0.5 * math.pi, math.pi)
        ctx.close_path()
        win = ctx.copy_path()
        ctx.clip()
        fl = max(math.exp(-(t - 2.6) * 7) if t > 2.6 else 0, math.exp(-(t - 3.3) * 7) if t > 3.3 else 0)
        rgba(ctx, (0.6, 0.65, 0.9), a2 * fl * 0.35)
        ctx.paint()
        if fl > 0.1:
            draw_bolt(ctx, (520, 500), (580, 820), t, a2 * fl, 1, seed=11, width=3)
        ctx.restore()
        ctx.new_path()
        ctx.append_path(win)
        ctx.set_line_width(3)
        rgba(ctx, WHITE, a2 * 0.85)
        ctx.stroke()
        draw_cup(ctx, t, a2)


# ---- Faraday kafesi açıklaması
def scene_cage(ctx, t, a):
    if a <= 0:
        return
    lt = t - 28.7
    cx, cy, R = 540, 960, 230
    ctx.set_line_width(2)
    rgba(ctx, WHITE, a * 0.9)
    ctx.arc(cx, cy, R, 0, 2 * math.pi)
    ctx.stroke()
    ctx.set_line_width(1.2)
    rgba(ctx, WHITE, a * 0.35)
    for k in (0.35, 0.7):
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(k, 1)
        ctx.arc(0, 0, R, 0, 2 * math.pi)
        ctx.restore()
        ctx.stroke()
    for f in (-0.6, 0.0, 0.6):
        y = cy + R * f
        rx = R * math.sqrt(1 - f * f)
        ctx.save()
        ctx.translate(cx, y)
        ctx.scale(1, 0.18)
        ctx.arc(0, 0, rx, 0, 2 * math.pi)
        ctx.restore()
        ctx.stroke()
    draw_person(ctx, cx, 1120, 190, WHITE, a)
    # yıldırım + kabuk akımı
    top, bot = (cx, cy - R), (cx, cy + R)
    grow = eo(seg(lt, 0.4, 0.7))
    draw_bolt(ctx, (cx - 60, 560), top, t, a, grow, seed=21)
    rev = eio(seg(lt, 0.8, 2.2))
    for sgn, ph in ((1, 0), (-1, 0.5)):
        path = [(cx + sgn * (R + 6) * math.cos(-math.pi / 2 + math.pi * k / 80),
                 cy + (R + 6) * math.sin(-math.pi / 2 + math.pi * k / 80)) for k in range(81)]
        draw_current(ctx, t, path, rev, a, ph)
    draw_bolt(ctx, (bot[0], bot[1] + 6), (cx + 40, 1330), t, a * 0.9, eo(seg(lt, 2.1, 2.4)), seed=22, width=3)
    # dış yüzeydeki yükler
    for k in range(14):
        ang = -math.pi / 2 + 2 * math.pi * k / 14
        ka = a * eo(seg(lt, 3.0 + k * 0.05, 3.3 + k * 0.05))
        x, y = cx + (R + 34) * math.cos(ang), cy + (R + 34) * math.sin(ang)
        ctx.set_line_width(2.5)
        rgba(ctx, BOLT, ka)
        ctx.move_to(x - 8, y)
        ctx.line_to(x + 8, y)
        ctx.move_to(x, y - 8)
        ctx.line_to(x, y + 8)
        ctx.stroke()
    text_c(ctx, "E = 0", cx, 870, 44, ORANGE, a * eo(seg(lt, 3.6, 4.0)), "b")


# ---- kapanış
def scene_cta(ctx, t, a):
    base.scene_cta(ctx, t, a)


def render_frame(ctx, t):
    ctx.new_path()
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()
    draw_grid(ctx, 0.7 * (window(t, 3.9, 29, 0.6) + window(t, 34.4, 39.8, 0.6)))
    scene_hook(ctx, t, 1 - eio(seg(t, 4.0, 4.4)))
    scene_plane(ctx, t, window(t, 4.0, 28.9, 0.45) + window(t, 34.6, 39.3, 0.45))
    scene_cage(ctx, t, window(t, 28.6, 34.8, 0.4))
    scene_cta(ctx, t, eio(seg(t, 39.2, 39.6)))
    if t < 34.6:
        stages = [(4.0, 11.0, 1, "kesit"), (11.0, 19.0, 2, "çarpma"),
                  (19.0, 28.7, 3, "akım yolu"), (28.7, 34.7, 4, "faraday kafesi")]
        for s0, s1, n, lab in stages:
            if s0 <= t < s1:
                draw_dots(ctx, n, eo(seg(t, 4.0, 4.4)))
                la = window(t, s0, s1, 0.3) if n > 1 else eo(seg(t, 4.0, 4.4)) * (1 - eio(seg(t, 10.7, 11.0)))
                text_c(ctx, lab, W / 2, 400, 26, (0.7, 0.7, 0.7), la)
    else:
        draw_dots(ctx, 4, 1, final=True)
    base.draw_captions(ctx, t)
    text_c(ctx, WATERMARK, W / 2, 1590, 24, (0.38, 0.38, 0.38), 1)


def main():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    if len(sys.argv) > 2 and sys.argv[1] == "--still":
        for s in sys.argv[2:]:
            render_frame(ctx, float(s))
            surf.write_to_png(f"still_{s}.png")
        return
    out = sys.argv[1] if len(sys.argv) > 1 else "faraday.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i in range(n):
        render_frame(ctx, i / FPS)
        surf.flush()
        ff.stdin.write(bytes(surf.get_data()))
        if i % 150 == 0:
            print(f"{i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main()
