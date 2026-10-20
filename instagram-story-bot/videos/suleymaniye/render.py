"""Süleymaniye: İs ve Ses — 9:16 minimal çizim videosu.

Kullanım:
  python3 render.py              -> suleymaniye.mp4
  python3 render.py --still 12.5 -> tek kare PNG (önizleme)
"""
import math
import random
import subprocess
import sys

import cairo

W, H, FPS, DUR = 1080, 1920, 30, 43.0

WHITE = (1, 1, 1)
GREY = (0.55, 0.55, 0.55)
DARK = (0.22, 0.22, 0.22)
ORANGE = (1.0, 0.55, 0.30)
BG = (0.018, 0.022, 0.04)
YELLOW = (1.0, 0.85, 0.32)
RED = (0.90, 0.30, 0.24)
BLUE = (0.33, 0.55, 0.95)
SOOT = (0.45, 0.45, 0.47)

CAP_Y = 1440
WATERMARK = "@hesabin"


# ---------------------------------------------------------------- yardımcılar
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def eio(x):
    x = clamp(x)
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eo(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def lerp(a, b, u):
    return a + (b - a) * u


def mix(c1, c2, u):
    return tuple(lerp(a, b, u) for a, b in zip(c1, c2))


def window(t, a, b, fade=0.4):
    """a..b aralığında görünür, kenarlarda yumuşak geçiş."""
    return eio(seg(t, a, a + fade)) * (1 - eio(seg(t, b - fade, b)))


def rgba(ctx, c, a):
    ctx.set_source_rgba(c[0], c[1], c[2], clamp(a))


def glow_dot(ctx, x, y, r, c, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r * 4)
    g.add_color_stop_rgba(0, c[0], c[1], c[2], 0.55 * a)
    g.add_color_stop_rgba(0.25, c[0], c[1], c[2], 0.18 * a)
    g.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
    ctx.set_source(g)
    ctx.arc(x, y, r * 4, 0, 2 * math.pi)
    ctx.fill()
    rgba(ctx, mix(c, WHITE, 0.35), a)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def glow_stroke(ctx, path, c, width, a, glow=1.0):
    """path: ctx üzerinde yol çizen fonksiyon."""
    if glow > 0:
        for wm, am in ((7, 0.05), (4, 0.09), (2.2, 0.16)):
            path()
            ctx.set_line_width(width * wm)
            rgba(ctx, c, a * am * glow)
            ctx.stroke()
    path()
    ctx.set_line_width(width)
    rgba(ctx, c, a)
    ctx.stroke()


def font(ctx, size, weight="r"):
    fam = {"t": "Inter Thin", "l": "Inter Light", "r": "Inter Display", "b": "Inter Display"}[weight]
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if weight == "b" else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def text_c(ctx, s, x, y, size, c, a, weight="r"):
    font(ctx, size, weight)
    w = ctx.text_extents(s).x_advance
    ctx.move_to(x - w / 2, y)
    rgba(ctx, c, a)
    ctx.show_text(s)


# ------------------------------------------------------------ altyazı / UI
# (başla, bitir, [(kelime, stil)], aralık, punto)   stil: n=gri, b=kalın beyaz, o=kalın turuncu
def caps():
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

    return [
        (0.10, 1.45, T("*Elektrik yok, *aspiratör yok."), 0.10, 50),
        (1.50, 4.15, T("*450 *yıl önce yanan *binlerce *kandilin isi bu duvarları neden *hiç *karartmadı?"), 0.075, 46),
        (4.40, 7.20, T("*Süleymaniye *Camii, 1557. Mimar Sinan."), 0.11, 44),
        (7.30, 10.0, T("Cevap duvarda değil, *havanın *yolunda."), 0.11, 44),
        (10.2, 12.8, T("*Pencerelerden giren temiz hava,"), 0.11, 44),
        (12.9, 15.4, T("kandillerin sıcağıyla *kubbeye *yükselir..."), 0.11, 44),
        (15.5, 20.0, T("...ve isi *tek *bir *noktaya taşır: ^İs ^Odası."), 0.11, 44),
        (20.5, 23.6, T("İs, odanın *tavanında *birikir ve kazınır."), 0.10, 44),
        (23.8, 27.0, T("*Su ve *arap *zamkıyla küplerde yoğrulur."), 0.10, 44),
        (27.2, 30.4, T("Sonuç: hattatların *en *kaliteli *mürekkebi."), 0.10, 44),
        (30.5, 32.3, T("Peki ya *ses?"), 0.12, 50),
        (32.4, 34.6, T("Kubbedeki *küpler sesi her köşeye *eşit dağıtır."), 0.09, 44),
        (34.8, 37.1, T("Mucize değil, ^aerodinamik."), 0.16, 60),
        (37.2, 39.3, T("*Mimar *Sinan bunu *450 *yıl önce çözdü."), 0.10, 44),
        (39.5, 43.2, T("*Kaydet, bir mimara *gönder."), 0.12, 46),
    ]


CAPS = caps()


def draw_captions(ctx, t):
    for start, end, toks, gap, size in CAPS:
        if t < start or t > end + 0.4:
            continue
        local = t - start
        out = 1 - eio(seg(t, end, end + 0.35))
        # yerleşim
        sw = {}
        words = []
        for w, st in toks:
            font(ctx, size, "b" if st != "n" else "r")
            words.append((w, st, ctx.text_extents(w).x_advance))
        font(ctx, size, "r")
        space = ctx.text_extents(" ").x_advance
        lines, cur, cw = [], [], 0
        for i, (w, st, ww) in enumerate(words):
            add = ww if not cur else ww + space
            if cur and cw + add > 930:
                lines.append((cur, cw))
                cur, cw = [], 0
                add = ww
            cur.append((i, w, st, ww))
            cw += add
        lines.append((cur, cw))
        lh = size * 1.38
        y0 = CAP_Y - (len(lines) - 1) * lh / 2
        for li, (ln, lw) in enumerate(lines):
            x = W / 2 - lw / 2
            y = y0 + li * lh
            for i, w, st, ww in ln:
                a = eo(seg(local, i * gap, i * gap + 0.28)) * out
                dy = 10 * (1 - a)
                font(ctx, size, "b" if st != "n" else "r")
                c = {"n": (0.66, 0.67, 0.70), "b": WHITE, "o": ORANGE}[st]
                ctx.move_to(x, y + dy)
                rgba(ctx, c, a)
                ctx.show_text(w)
                if st == "b":
                    u = eo(seg(local, i * gap + 0.15, i * gap + 0.5)) * out
                    rgba(ctx, ORANGE, u * 0.85)
                    ctx.rectangle(x, y + 12, ww * u, 3)
                    ctx.fill()
                x += ww + space
        del sw


def draw_dots(ctx, active, a, final=False, frac=1.0):
    """Üstte 4 parçalı ilerleme çubuğu (aktif parça frac kadar dolu)."""
    if a <= 0:
        return
    x0, x1, y, h, gap = 120, 960, 290, 5, 10
    sw = (x1 - x0 - 3 * gap) / 4

    def bar(x, w):
        if w <= 0:
            return
        r = h / 2
        ctx.new_sub_path()
        ctx.arc(x + r, y + r, r, math.pi / 2, 3 * math.pi / 2)
        ctx.arc(x + max(r, w - r), y + r, r, -math.pi / 2, math.pi / 2)
        ctx.close_path()
        ctx.fill()

    for i in range(4):
        x = x0 + i * (sw + gap)
        rgba(ctx, WHITE, a * 0.16)
        bar(x, sw)
        if final:
            rgba(ctx, ORANGE, a)
            bar(x, sw)
        elif i < active - 1:
            rgba(ctx, WHITE, a * 0.9)
            bar(x, sw)
        elif i == active - 1:
            rgba(ctx, WHITE, a * 0.9)
            bar(x, sw * clamp(frac))


def stage_label(ctx, n, lab, a):
    """Sol üstte '01  KESİT' biçiminde bölüm etiketi."""
    if a <= 0:
        return
    font(ctx, 24, "b")
    ctx.move_to(120, 345)
    rgba(ctx, ORANGE, a)
    ctx.show_text(f"{n:02d}")
    x = 172
    font(ctx, 22, "r")
    rgba(ctx, (0.7, 0.72, 0.76), a)
    for ch in lab.upper():
        ctx.move_to(x, 345)
        ctx.show_text(ch)
        x += ctx.text_extents(ch).x_advance + 3


def paint_bg(ctx):
    ctx.new_path()
    ctx.set_source_rgb(*BG)
    ctx.paint()
    g = cairo.RadialGradient(W / 2, 900, 50, W / 2, 900, 1000)
    g.add_color_stop_rgba(0, 0.07, 0.08, 0.12, 0.9)
    g.add_color_stop_rgba(1, 0.07, 0.08, 0.12, 0)
    ctx.set_source(g)
    ctx.paint()


def draw_frame(ctx, a):
    """Çizim alanının köşelerinde vizör köşelikleri."""
    if a <= 0:
        return
    x0, y0, x1, y1, L = 80, 470, 1000, 1335, 34
    ctx.set_line_width(2)
    for cx, cy, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        ctx.move_to(cx + sx * L, cy)
        ctx.line_to(cx, cy)
        ctx.line_to(cx, cy + sy * L)
    rgba(ctx, WHITE, 0.32 * a)
    ctx.stroke()


def draw_watermark(ctx):
    rgba(ctx, ORANGE, 0.9)
    ctx.arc(126, 1591, 5, 0, 2 * math.pi)
    ctx.fill()
    font(ctx, 24, "r")
    ctx.move_to(142, 1600)
    rgba(ctx, (0.45, 0.46, 0.5), 1)
    ctx.show_text(WATERMARK)


def draw_grid(ctx, a):
    if a <= 0:
        return
    step = 54
    rgba(ctx, WHITE, 0.16 * a)
    for i in range(0, W // step + 1):
        for j in range(0, H // step + 1):
            ctx.rectangle(i * step + 26, j * step + 11, 2, 2)
    ctx.fill()
    # kenarları karart (vinyet)
    g = cairo.RadialGradient(W / 2, 960, 300, W / 2, 960, 1150)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, BG[0], BG[1], BG[2], 0.85 * a)
    ctx.set_source(g)
    ctx.paint()


# ------------------------------------------------------------- 3B model
def circle_pts(cx, cy, cz, r, n=40, axis="y", a0=0.0, a1=2 * math.pi):
    pts = []
    for k in range(n + 1):
        a = lerp(a0, a1, k / n)
        if axis == "y":
            pts.append((cx + r * math.cos(a), cy, cz + r * math.sin(a)))
        elif axis == "x":
            pts.append((cx, cy + r * math.sin(a), cz + r * math.cos(a)))
        else:
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), cz))
    return pts


def rect_x(x, z0, z1, y0, y1):
    return [(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0), (x, y0, z0)]


def rect_z(z, x0, x1, y0, y1):
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), (x0, y0, z)]


def build_model():
    """(nokta listesi, grup) çiftleri. Ölçüler metre benzeri, kaba şematik."""
    L = []
    hw, wh = 29, 25
    # zemin + duvarlar
    L.append(([(-hw, 0, -hw), (hw, 0, -hw), (hw, 0, hw), (-hw, 0, hw), (-hw, 0, -hw)], "walls"))
    L.append(([(-hw, wh, -hw), (hw, wh, -hw), (hw, wh, hw), (-hw, wh, hw), (-hw, wh, -hw)], "walls"))
    for x in (-hw, hw):
        for z in (-hw, hw):
            L.append(([(x, 0, z), (x, wh, z)], "walls"))
    # pencereler (yan duvarlar)
    for x in (-hw, hw):
        for zc in (-20, -12, -4, 4, 12, 20):
            for y0, y1 in ((3, 8), (11, 16.5)):
                L.append((rect_x(x, zc - 2, zc + 2, y0, y1), "win"))
    # kıble ve giriş duvarı pencereleri
    for z in (-hw, hw):
        for xc in (-20, -12, 12, 20):
            for y0, y1 in ((3, 8), (11, 16.5)):
                L.append((rect_z(z, xc - 2, xc + 2, y0, y1), "win"))
    # ana kapı (giriş, z=-29)
    L.append(([(-3.5, 0, -hw), (-3.5, 12, -hw), (0, 15, -hw), (3.5, 12, -hw), (3.5, 0, -hw)], "win"))
    # kemerler (x=±13 düzleminde)
    for x in (-13, 13):
        L.append((circle_pts(x, 25, 0, 13, 30, "x", 0, math.pi), "arch"))
        L.append(([(x, 0, -13), (x, 25, -13)], "arch"))
        L.append(([(x, 0, 13), (x, 25, 13)], "arch"))
    # yarım kubbeler (z yönünde)
    R = 13
    for s in (-1, 1):
        cz = 13 * s
        for k in range(9):
            ph = math.pi * k / 8
            pts = []
            for j in range(13):
                th = (math.pi / 2) * j / 12
                pts.append((R * math.cos(th) * math.cos(ph), 25 + R * math.sin(th),
                            cz + s * R * math.cos(th) * math.sin(ph)))
            L.append((pts, "semi"))
        for th in (0.0, 0.45, 0.9):
            r = R * math.cos(th)
            pts = [(r * math.cos(math.pi * k / 24), 25 + R * math.sin(th),
                    cz + s * r * math.sin(math.pi * k / 24)) for k in range(25)]
            L.append((pts, "semi"))
    # ana kubbe
    yc = 38
    L.append((circle_pts(0, yc, 0, R, 48), "dome"))
    L.append((circle_pts(0, yc - 4, 0, R, 48), "dome"))  # kasnak
    for k in range(16):
        ph = 2 * math.pi * k / 16
        L.append(([(R * math.cos(ph), yc - 4, R * math.sin(ph)), (R * math.cos(ph), yc, R * math.sin(ph))], "dome"))
    for k in range(16):
        ph = 2 * math.pi * k / 16
        pts = [(R * math.cos(th) * math.cos(ph), yc + R * math.sin(th), R * math.cos(th) * math.sin(ph))
               for th in [(math.pi / 2) * j / 14 for j in range(15)]]
        L.append((pts, "dome"))
    for th in (0.4, 0.8, 1.15):
        L.append((circle_pts(0, yc + R * math.sin(th), 0, R * math.cos(th), 40), "dome"))
    # yan sahın küçük kubbeleri
    for x in (-21, 21):
        for zc in (-19.5, -6.5, 6.5, 19.5):
            L.append((circle_pts(x, wh, zc, 4, 20), "small"))
            for ph in (0, math.pi / 2):
                pts = [(x + 4 * math.cos(a) * math.cos(ph), wh + 4 * math.sin(a), zc + 4 * math.cos(a) * math.sin(ph))
                       for a in [math.pi * j / 12 for j in range(13)]]
                L.append((pts, "small"))
    # minareler
    for x in (-31.5, 31.5):
        z = -32
        for k in range(6):
            ph = 2 * math.pi * k / 6
            L.append(([(x + 1.3 * math.cos(ph), 0, z + 1.3 * math.sin(ph)),
                       (x + 1.3 * math.cos(ph), 62, z + 1.3 * math.sin(ph))], "minaret"))
        for y in (30, 43, 55):
            L.append((circle_pts(x, y, z, 2.3, 16), "minaret"))
        L.append((circle_pts(x, 62, z, 1.3, 12), "minaret"))
        for k in range(6):
            ph = 2 * math.pi * k / 6
            L.append(([(x + 1.3 * math.cos(ph), 62, z + 1.3 * math.sin(ph)), (x, 71, z)], "minaret"))
    return L


MODEL = build_model()
ISO = dict(x0=-3, x1=3, y0=17.5, y1=22.5, z0=-29, z1=-26.5)  # İs Odası (giriş kapısı üstü)
_rnd = random.Random(7)
ORDER = {"walls": 0, "win": 1, "arch": 2, "semi": 3, "dome": 4, "small": 5, "minaret": 6}
MODEL.sort(key=lambda it: ORDER[it[1]])
STAGGER = [i / len(MODEL) + _rnd.uniform(-0.03, 0.03) for i in range(len(MODEL))]


class Cam:
    def __init__(self, yaw, pitch, scale, ty, cx=W / 2, cy=960, dist=320):
        self.yaw, self.pitch, self.scale, self.ty = yaw, pitch, scale, ty
        self.cx, self.cy, self.dist = cx, cy, dist

    def p(self, pt):
        x, y, z = pt
        y -= self.ty
        cy_, sy_ = math.cos(self.yaw), math.sin(self.yaw)
        x1 = x * cy_ - z * sy_
        z1 = x * sy_ + z * cy_
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        y2 = y * cp - z1 * sp
        z2 = y * sp + z1 * cp
        d = z2 + self.dist
        f = self.scale * self.dist
        return self.cx + f * x1 / d, self.cy - f * y2 / d, d


def cam_at(t):
    d = math.radians
    if t < 9.0:
        u = eio(seg(t, 4.0, 9.0))
        return Cam(d(lerp(18, 48, u)), d(15), 9.4, 34)
    if t < 30:
        u = eio(seg(t, 9.0, 10.9))
        return Cam(d(lerp(48, 60, u)), d(lerp(15, 9, u)), lerp(9.4, 12.2, u), lerp(34, 24, u))
    u = seg(t, 34.6, 39.6)
    return Cam(d(lerp(60, 72, u)), d(lerp(9, 12, u)), lerp(12.2, 11.6, u), 24)


def near_sign(cam):
    """Kameraya yakın yan duvarın x işareti (kesit için)."""
    return 1 if cam.p((29, 10, 0))[2] < cam.p((-29, 10, 0))[2] else -1


def draw_model(ctx, t, cam, a, build_t0=4.3, build_dur=4.2, cut=0.0, minaret_a=1.0):
    ns = near_sign(cam)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for (pts, grp), st in zip(MODEL, STAGGER):
        r = seg(t, build_t0 + st * build_dur, build_t0 + st * build_dur + 0.9)
        if r <= 0:
            continue
        r = eo(r)
        ga = a
        if grp == "minaret":
            ga *= minaret_a
        if ga <= 0.01:
            continue
        # kesit: kameraya yakın yarıyı soldur
        mx = sum(p[0] for p in pts) / len(pts)
        if cut > 0 and mx * ns > 2:
            ga *= lerp(1, 0.12, cut)
        sp = [cam.p(p) for p in pts]
        n = len(sp) - 1
        upto = r * n
        k = int(upto)
        frac = upto - k
        path = sp[: k + 1]
        if k < n:
            x0, y0, d0 = sp[k]
            x1, y1, d1 = sp[k + 1]
            path = path + [(lerp(x0, x1, frac), lerp(y0, y1, frac), d0)]
        depth = sum(p[2] for p in sp) / len(sp)
        dcue = clamp(1.25 - (depth - (cam.dist - 30)) / 80, 0.35, 1.0)
        w = 1.5 if grp in ("win", "small") else 1.9
        ctx.move_to(path[0][0], path[0][1])
        for x, y, _ in path[1:]:
            ctx.line_to(x, y)
        ctx.set_line_width(w * 3)
        rgba(ctx, WHITE, ga * dcue * 0.07)
        ctx.stroke_preserve()
        ctx.set_line_width(w)
        rgba(ctx, WHITE, ga * dcue * (0.55 if grp == "win" else 0.85))
        ctx.stroke()


def draw_iso_room(ctx, cam, a, pulse):
    if a <= 0:
        return
    c = ISO
    corners = [(x, y, z) for x in (c["x0"], c["x1"]) for y in (c["y0"], c["y1"]) for z in (c["z0"], c["z1"])]
    edges = [(i, j) for i in range(8) for j in range(i + 1, 8)
             if sum(corners[i][k] != corners[j][k] for k in range(3)) == 1]
    sp = [cam.p(p) for p in corners]

    def path():
        for i, j in edges:
            ctx.move_to(sp[i][0], sp[i][1])
            ctx.line_to(sp[j][0], sp[j][1])

    glow_stroke(ctx, path, ORANGE, 2.4, a, glow=0.6 + 0.6 * pulse)
    # etiket
    cx = sum(p[0] for p in sp) / 8
    cy = sum(p[1] for p in sp) / 8
    font(ctx, 30, "b")
    tw = ctx.text_extents("İS ODASI").x_advance
    lx, ly = min(cx + 70, W - 40 - tw - 50), cy - 150
    ctx.set_line_width(1.5)
    rgba(ctx, ORANGE, a * 0.8)
    ctx.move_to(cx + 14, cy - 18)
    ctx.line_to(lx, ly + 10)
    ctx.line_to(lx + 40, ly + 10)
    ctx.stroke()
    ctx.move_to(lx + 50, ly + 20)
    rgba(ctx, ORANGE, a)
    ctx.show_text("İS ODASI")


# lamba halkası
LAMPS = [(10.5 * math.cos(2 * math.pi * k / 28), 5.0, 10.5 * math.sin(2 * math.pi * k / 28)) for k in range(28)]


def draw_lamps(ctx, t, cam, a):
    if a <= 0:
        return
    rng = random.Random(3)
    pts = []
    for i, p in enumerate(LAMPS):
        r = seg(t, 10.0 + i * 0.03, 10.4 + i * 0.03)
        if r <= 0:
            continue
        x, y, d = cam.p(p)
        tx, ty_, _ = cam.p((p[0] * 0.55, 34, p[2] * 0.55))
        ctx.move_to(x, y)
        ctx.line_to(lerp(x, tx, r), lerp(y, ty_, r))
        pts.append((x, y, r, rng.random()))
    ctx.set_line_width(0.8)
    rgba(ctx, WHITE, 0.16 * a)
    ctx.stroke()
    for x, y, r, ph in pts:
        fl = 0.75 + 0.25 * math.sin(t * 13 + ph * 40) * math.sin(t * 7.3 + ph * 11)
        glow_dot(ctx, x, y, 3.2, ORANGE, a * r * fl)


# hava akışı yolları
def catmull(pts, n=220):
    P = [pts[0]] + pts + [pts[-1]]
    raw = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(12):
            u = s / 12
            u2, u3 = u * u, u * u * u
            raw.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u3) for k in range(3)))
    raw.append(pts[-1])
    # eşit aralıklı yeniden örnekle
    acc = [0.0]
    for i in range(1, len(raw)):
        acc.append(acc[-1] + math.dist(raw[i - 1], raw[i]))
    tot = acc[-1]
    out, j = [], 0
    for s in range(n + 1):
        target = tot * s / n
        while j < len(acc) - 2 and acc[j + 1] < target:
            j += 1
        u = (target - acc[j]) / max(1e-9, acc[j + 1] - acc[j])
        out.append(tuple(lerp(raw[j][k], raw[j + 1][k], u) for k in range(3)))
    return out


def build_flows(far):
    tail = [(0, 49, 0), (0, 47.5, -7), (0, 41, -13), (0, 35, -19.5), (0, 28, -24.5), (0, 20, -27.6)]
    f = far
    flows = [
        [(f * 29, 5.5, 16), (f * 20, 4.5, 12), (f * 9, 5.5, 7), (f * 6, 18, 5), (f * 3, 36, 3)] + tail,
        [(f * 29, 13.5, -4), (f * 20, 9, -3), (f * 10, 6, -2), (f * 7, 20, -1), (f * 3, 38, -1)] + tail,
        [(f * 29, 5.5, -20), (f * 19, 4.5, -14), (f * 8, 5.5, -9), (f * 5, 19, -6), (f * 2, 39, -3)] + tail,
        [(-12, 13.5, 29), (-9, 9, 20), (-6, 6, 11), (-4, 19, 7), (-2, 39, 3)] + tail,
        [(12, 5.5, 29), (9, 4.5, 21), (7, 5.5, 11), (4, 20, 6), (1, 40, 2)] + tail,
    ]
    return [catmull(p) for p in flows]


FLOWS = {s: build_flows(-s) for s in (-1, 1)}


def flow_color(u):
    if u < 0.3:
        return mix(YELLOW, ORANGE, u / 0.3)
    if u < 0.7:
        return ORANGE
    return mix(ORANGE, (0.95, 0.45, 0.15), (u - 0.7) / 0.3)


def draw_flows(ctx, t, cam, a, reveal_t0, converge):
    """converge: 0..1 — yolların İs Odası'na giden kuyruk kısmının görünürlüğü."""
    if a <= 0:
        return
    flows = FLOWS[near_sign(cam)]
    for fi, path in enumerate(flows):
        n = len(path) - 1
        # gösterilecek en uç: önce pencere->kubbe (u 0..0.55), sonra kuyruk
        rev = 0.58 * eo(seg(t, reveal_t0 + fi * 0.25, reveal_t0 + fi * 0.25 + 2.6)) + 0.42 * eo(converge)
        k_max = int(rev * n)
        if k_max < 2:
            continue
        sp = [cam.p(p) for p in path[: k_max + 1]]
        # silik iz
        for i in range(1, len(sp)):
            c = flow_color(i / n)
            ctx.move_to(sp[i - 1][0], sp[i - 1][1])
            ctx.line_to(sp[i][0], sp[i][1])
            ctx.set_line_width(1.6)
            rgba(ctx, c, 0.28 * a)
            ctx.stroke()
        # oklar
        for au in (0.12, 0.3, 0.48, 0.66, 0.84):
            k = int(au * n)
            if k + 3 > k_max:
                continue
            x0, y0, _ = sp[k - 3]
            x1, y1, _ = sp[k + 3]
            ang = math.atan2(y1 - y0, x1 - x0)
            x, y = sp[k][0], sp[k][1]
            s = 13
            c = flow_color(au)

            def arrow(x=x, y=y, ang=ang, s=s):
                ctx.move_to(x - s * math.cos(ang - 0.55), y - s * math.sin(ang - 0.55))
                ctx.line_to(x, y)
                ctx.line_to(x - s * math.cos(ang + 0.55), y - s * math.sin(ang + 0.55))

            glow_stroke(ctx, arrow, c, 2.6, a * 0.95, glow=0.7)
        # akan parçacıklar
        for j in range(7):
            u = ((t * 0.16 + j / 7 + fi * 0.13) % 1.0)
            k = int(u * n)
            if k < 6 or k > k_max:
                continue
            tail = [sp[i] for i in range(k - 6, k + 1)]
            c = flow_color(u)

            def streak(tail=tail):
                ctx.move_to(tail[0][0], tail[0][1])
                for p in tail[1:]:
                    ctx.line_to(p[0], p[1])

            glow_stroke(ctx, streak, c, 3.0, a, glow=1.0)
            # is parçacıkları (gri) — kuyrukta
            if u > 0.55:
                rnd = random.Random(j * 31 + fi)
                for q in range(3):
                    ox, oy = rnd.uniform(-9, 9), rnd.uniform(-9, 9)
                    rgba(ctx, SOOT, a * 0.7)
                    ctx.arc(sp[k][0] + ox, sp[k][1] + oy, 2.0, 0, 2 * math.pi)
                    ctx.fill()


def scene_3d(ctx, t, a):
    cam = cam_at(t)
    cut = eio(seg(t, 9.2, 10.8))
    minaret_a = 1 - eio(seg(t, 9.0, 10.2))
    if t > 34:
        minaret_a = 0.0
    draw_model(ctx, t, cam, a, cut=cut, minaret_a=minaret_a)
    lamp_a = a * (1 if t < 30 else 1)
    draw_lamps(ctx, t if t < 30 else 30, cam, lamp_a)
    if t < 30:
        conv = seg(t, 15.4, 17.6)
        draw_flows(ctx, t, cam, a, 10.6, conv)
        iso_a = a * eo(seg(t, 16.6, 17.4))
        pulse = 0.5 + 0.5 * math.sin(t * 5)
        draw_iso_room(ctx, cam, iso_a, pulse)
    else:
        draw_flows(ctx, t, cam, a, -10, 1.0)
        draw_iso_room(ctx, cam, a, 0.5 + 0.5 * math.sin(t * 5))


# ----------------------------------------------------------------- sahne 0
def draw_bolt(ctx, cx, cy, s):
    pts = [(0.15, -1), (-0.55, 0.12), (-0.02, 0.12), (-0.2, 1), (0.55, -0.15), (0.02, -0.15), (0.15, -1)]
    ctx.move_to(cx + pts[0][0] * s, cy + pts[0][1] * s)
    for x, y in pts[1:]:
        ctx.line_to(cx + x * s, cy + y * s)
    ctx.close_path()


def draw_fan(ctx, cx, cy, s, rot):
    ctx.new_sub_path()
    ctx.arc(cx, cy, s, 0, 2 * math.pi)
    for k in range(3):
        a0 = rot + 2 * math.pi * k / 3
        ctx.move_to(cx, cy)
        ctx.curve_to(cx + 0.7 * s * math.cos(a0 - 0.2), cy + 0.7 * s * math.sin(a0 - 0.2),
                     cx + 0.85 * s * math.cos(a0 + 0.35), cy + 0.85 * s * math.sin(a0 + 0.35),
                     cx + 0.25 * s * math.cos(a0 + 0.6), cy + 0.25 * s * math.sin(a0 + 0.6))
    ctx.new_sub_path()
    ctx.arc(cx, cy, s * 0.1, 0, 2 * math.pi)


def draw_kandil(ctx, cx, cy, t, ph, a):
    # cam kase
    ctx.move_to(cx - 26, cy)
    ctx.curve_to(cx - 26, cy + 34, cx + 26, cy + 34, cx + 26, cy)
    ctx.move_to(cx - 30, cy)
    ctx.line_to(cx + 30, cy)
    ctx.set_line_width(2)
    rgba(ctx, WHITE, 0.85 * a)
    ctx.stroke()
    # askı
    ctx.move_to(cx - 26, cy)
    ctx.line_to(cx, cy - 80)
    ctx.line_to(cx + 26, cy)
    ctx.set_line_width(1)
    rgba(ctx, WHITE, 0.3 * a)
    ctx.stroke()
    # alev
    fl = 1 + 0.12 * math.sin(t * 17 + ph) + 0.08 * math.sin(t * 29 + ph * 3)
    h = 26 * fl
    g = cairo.RadialGradient(cx, cy - 8, 0, cx, cy - 8, 70)
    g.add_color_stop_rgba(0, ORANGE[0], ORANGE[1], ORANGE[2], 0.45 * a)
    g.add_color_stop_rgba(1, ORANGE[0], ORANGE[1], ORANGE[2], 0)
    ctx.set_source(g)
    ctx.arc(cx, cy - 8, 70, 0, 2 * math.pi)
    ctx.fill()
    ctx.move_to(cx, cy - h)
    ctx.curve_to(cx + 10, cy - h * 0.5, cx + 9, cy, cx, cy)
    ctx.curve_to(cx - 9, cy, cx - 10, cy - h * 0.5, cx, cy - h)
    rgba(ctx, mix(ORANGE, WHITE, 0.25), a)
    ctx.fill()


def scene_hook(ctx, t, a):
    if a <= 0:
        return
    # 0 - 1.5: elektrik / aspiratör yok
    a1 = a * (1 - eio(seg(t, 1.25, 1.55)))
    if a1 > 0:
        for i, (cx, kind) in enumerate(((380, "bolt"), (700, "fan"))):
            ap = a1 * eo(seg(t, 0.1 + i * 0.35, 0.45 + i * 0.35))
            cy = 940
            ctx.set_line_width(3)
            rgba(ctx, WHITE, ap)
            if kind == "bolt":
                draw_bolt(ctx, cx, cy, 95)
            else:
                draw_fan(ctx, cx, cy, 95, t * 3 * (1 - seg(t, 0.6, 1.2)))
            ctx.stroke()
            s = eo(seg(t, 0.45 + i * 0.35, 0.7 + i * 0.35))
            if s > 0:
                def strike(cx=cx, s=s):
                    ctx.move_to(cx - 120, cy + 120)
                    ctx.line_to(cx - 120 + 240 * s, cy + 120 - 240 * s)
                glow_stroke(ctx, strike, RED, 5, a1, glow=0.8)
    # 1.5 - 4.2: 450 yıl + kandiller
    a2 = a * eo(seg(t, 1.45, 1.8))
    if a2 > 0:
        n = int(450 * eo(seg(t, 1.5, 2.6)))
        text_c(ctx, str(n), W / 2, 760, 200, WHITE, a2, "t")
        text_c(ctx, "yıl önce", W / 2, 820, 30, GREY, a2)
        # kandil sırası + yükselen is
        for i in range(5):
            cx = 220 + i * 160
            cy = 1150 + (20 if i % 2 else 0)
            ap = a2 * eo(seg(t, 1.8 + i * 0.12, 2.2 + i * 0.12))
            draw_kandil(ctx, cx, cy, t, i * 1.7, ap)
            # is dumanı
            sm = seg(t, 2.3 + i * 0.1, 4.0)
            if sm > 0:
                ctx.move_to(cx, cy - 30)
                hh = 260 * eo(sm)
                for q in range(1, 25):
                    yy = cy - 30 - hh * q / 24
                    ctx.line_to(cx + 14 * math.sin(q * 0.55 + t * 2.5 + i), yy)
                ctx.set_line_width(2.4)
                rgba(ctx, SOOT, ap * 0.6)
                ctx.stroke()
        # soru işareti: duvar neden kararmadı
        q = eo(seg(t, 3.0, 3.5))
        if q > 0:
            text_c(ctx, "?", W / 2, 1000, 90, ORANGE, a2 * q, "l")


# ----------------------------------------------------------------- sahne 3: mürekkep
def step_header(ctx, t, a, step):
    """Üstte 1 — 2 — 3 adım göstergesi."""
    xs = [W / 2 - 200, W / 2, W / 2 + 200]
    y = 540
    fill = clamp((t - 20.4) / 9.6) * 2
    ctx.set_line_width(2)
    rgba(ctx, DARK, a)
    ctx.move_to(xs[0], y)
    ctx.line_to(xs[2], y)
    ctx.stroke()
    rgba(ctx, ORANGE, a)
    ctx.move_to(xs[0], y)
    ctx.line_to(xs[0] + 200 * min(fill, step), y)
    ctx.stroke()
    labels = ["is", "küp", "mürekkep"]
    for i, x in enumerate(xs):
        done = i <= step
        rgba(ctx, BG, a)
        ctx.arc(x, y, 24, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_line_width(2)
        rgba(ctx, ORANGE if done else DARK, a)
        ctx.arc(x, y, 24, 0, 2 * math.pi)
        ctx.stroke()
        text_c(ctx, str(i + 1), x, y + 10, 28, ORANGE if done else GREY, a, "b")
        text_c(ctx, labels[i], x, y + 62, 24, WHITE if i == step else GREY, a * (1 if i == step else 0.6))


def ink_step1(ctx, t, a):
    lt = t - 20.4
    # oda kutusu
    x0, y0, x1, y1, dx, dy = 360, 820, 720, 1120, 70, -60

    def box():
        ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
        ctx.move_to(x0, y0)
        ctx.line_to(x0 + dx, y0 + dy)
        ctx.line_to(x1 + dx, y0 + dy)
        ctx.line_to(x1, y0)
        ctx.move_to(x1 + dx, y0 + dy)
        ctx.line_to(x1 + dx, y1 + dy)
        ctx.line_to(x1, y1)

    ctx.set_line_width(2)
    rgba(ctx, WHITE, a * 0.85)
    box()
    ctx.stroke()
    # giriş açıklığı (sol)
    rgba(ctx, BG, a)
    ctx.rectangle(x0 - 4, 1000, 8, 70)
    ctx.fill()
    # gelen akış
    for j in range(10):
        u = (lt * 0.5 + j / 10) % 1
        px = lerp(120, x0 + 60, u)
        py = 1035 + 8 * math.sin(u * 9 + j)
        c = mix(ORANGE, SOOT, u)
        glow_dot(ctx, px, py, 3, c, a * (1 - u * 0.4))
    # tavana yükselen is
    rnd = random.Random(5)
    for j in range(26):
        sx = rnd.uniform(x0 + 40, x1 - 40)
        ph = rnd.random()
        u = (lt * 0.6 + ph) % 1
        px = lerp(x0 + 50, sx, eo(u))
        py = lerp(1035, y0 + 20, eo(u))
        rgba(ctx, SOOT, a * (1 - u) * 0.9)
        ctx.arc(px, py, 2.6, 0, 2 * math.pi)
        ctx.fill()
    # tavan is katmanı
    thick = 26 * eo(seg(lt, 0.2, 1.8))
    scrape = eio(seg(lt, 1.8, 3.0))
    sx = lerp(x0, x1, scrape)
    if thick > 0:
        rgba(ctx, (0.33, 0.33, 0.35), a)
        ctx.rectangle(sx, y0 + 2, x1 - sx - 2, thick)
        ctx.fill()
    # kazıyıcı
    if 1.7 < lt:
        ca = a * (1 - seg(lt, 3.0, 3.2))
        ctx.set_line_width(4)
        rgba(ctx, WHITE, ca)
        ctx.move_to(sx, y0 + 4)
        ctx.line_to(sx, y0 + 34)
        ctx.stroke()
        ctx.set_line_width(2.5)
        ctx.move_to(sx, y0 + 30)
        ctx.line_to(sx - 70, y0 + 120)
        ctx.stroke()
        # düşen is
        for j in range(6):
            u = (lt * 2 + j / 6) % 1
            rgba(ctx, SOOT, ca * (1 - u))
            ctx.arc(sx - 5 + 4 * j % 7, lerp(y0 + 30, 1080, u), 2.5, 0, 2 * math.pi)
            ctx.fill()
    # kase
    bx, by = 600, 1085
    pile = eo(seg(lt, 1.9, 3.1))
    ctx.set_line_width(2)
    rgba(ctx, WHITE, a * 0.85)
    ctx.move_to(bx - 60, by)
    ctx.curve_to(bx - 60, by + 34, bx + 60, by + 34, bx + 60, by)
    ctx.stroke()
    if pile > 0:
        rgba(ctx, (0.33, 0.33, 0.35), a)
        ctx.move_to(bx - 50, by + 2)
        ctx.curve_to(bx - 30, by - 30 * pile, bx + 30, by - 30 * pile, bx + 50, by + 2)
        ctx.close_path()
        ctx.fill()
    text_c(ctx, "is", x1 + 120, y0 + 30, 26, GREY, a * eo(seg(lt, 0.8, 1.2)))
    text_c(ctx, "is tozu", bx, by + 70, 24, GREY, a * pile)


def jar_path(ctx, cx, top, s=1.0):
    ctx.move_to(cx - 45 * s, top)
    ctx.curve_to(cx - 45 * s, top + 30 * s, cx - 125 * s, top + 50 * s, cx - 120 * s, top + 140 * s)
    ctx.curve_to(cx - 115 * s, top + 230 * s, cx - 60 * s, top + 290 * s, cx - 50 * s, top + 320 * s)
    ctx.line_to(cx + 50 * s, top + 320 * s)
    ctx.curve_to(cx + 60 * s, top + 290 * s, cx + 115 * s, top + 230 * s, cx + 120 * s, top + 140 * s)
    ctx.curve_to(cx + 125 * s, top + 50 * s, cx + 45 * s, top + 30 * s, cx + 45 * s, top)


def ink_step2(ctx, t, a):
    lt = t - 23.8
    cx, top = 600, 830
    # su kanalı
    cy0, cy1 = 760, 790
    ctx.set_line_width(2)
    rgba(ctx, WHITE, a * 0.8)
    ctx.move_to(130, cy0)
    ctx.line_to(470, cy0)
    ctx.move_to(130, cy1)
    ctx.line_to(470, cy1)
    ctx.line_to(490, cy1 + 10)
    ctx.stroke()
    # akan su çizgileri
    ctx.set_line_width(3)
    for j in range(8):
        u = (lt * 0.7 + j / 8) % 1
        x = lerp(130, 470, u)
        rgba(ctx, BLUE, a * 0.9)
        ctx.move_to(x, 775)
        ctx.line_to(x + 22, 775)
        ctx.stroke()
    # düşen su
    def stream():
        ctx.move_to(490, 800)
        ctx.curve_to(520, 805, 560, 820, 575, top + 20)
    glow_stroke(ctx, stream, BLUE, 3.5, a * 0.9, glow=0.6)
    text_c(ctx, "su", 300, 740, 26, BLUE, a)
    # küp
    ctx.save()
    jar_path(ctx, cx, top)
    ctx.close_path()
    ctx.clip()
    lvl = eo(seg(lt, 0.2, 2.8))
    ly = top + 320 - 280 * lvl
    rgba(ctx, (0.15, 0.15, 0.17), a)
    ctx.rectangle(cx - 140, ly, 280, 400)
    ctx.fill()
    # karıştırma girdabı
    ctx.set_line_width(1.6)
    rgba(ctx, WHITE, a * 0.25)
    for k in range(3):
        ctx.new_sub_path()
        r = 22 + k * 22
        ctx.arc(cx, ly + 90, r, lt * 3 + k, lt * 3 + k + 2.2)
    ctx.stroke()
    ctx.restore()
    ctx.set_line_width(2.4)
    rgba(ctx, WHITE, a * 0.9)
    jar_path(ctx, cx, top)
    ctx.stroke()
    ctx.move_to(cx - 55, top)
    ctx.line_to(cx + 55, top)
    ctx.stroke()
    # yüzey çizgisi
    if lvl > 0.05:
        def surf():
            hw = 100 if lvl > 0.3 else 70
            ctx.move_to(cx - hw, ly)
            ctx.line_to(cx + hw, ly)
        ctx.save()
        jar_path(ctx, cx, top)
        ctx.close_path()
        ctx.clip()
        glow_stroke(ctx, surf, ORANGE, 2, a * 0.8, glow=0.6)
        ctx.restore()
    # yukarıdan is
    for j in range(12):
        u = (lt * 0.9 + j / 12) % 1
        x = 650 + 18 * math.sin(j * 2.1) - 40 * u
        y = lerp(660, top + 10, u)
        rgba(ctx, SOOT, a * (1 - u * 0.3))
        ctx.arc(x, y, 3, 0, 2 * math.pi)
        ctx.fill()
    text_c(ctx, "is", 700, 660, 26, GREY, a)
    # zamk damlaları
    for j in range(2):
        u = (lt * 0.6 + j / 2) % 1
        x, y = 560, lerp(680, top + 10, u * u)
        glow_dot(ctx, x, y, 6, (0.95, 0.72, 0.3), a)
    text_c(ctx, "zamk", 480, 690, 26, (0.95, 0.72, 0.3), a)


def ink_step3(ctx, t, a):
    lt = t - 27.2
    ctx.save()
    ctx.translate(W / 2, 960)
    ctx.rotate(math.radians(-4))
    # kağıt
    rgba(ctx, (0.93, 0.90, 0.82), a)
    ctx.rectangle(-230, -210, 460, 380)
    ctx.fill()
    rgba(ctx, ORANGE, a * 0.6)
    ctx.set_line_width(1.2)
    ctx.rectangle(-212, -192, 424, 344)
    ctx.stroke()
    # kalem yolu: elif + nun benzeri bir kıvrım
    path = []
    for k in range(40):  # elif
        path.append((-120 + 4 * k / 40, -150 + 260 * k / 40))
    gap = len(path)
    for k in range(80):  # nun çanağı
        ang = lerp(-0.2, math.pi + 0.15, k / 79)
        path.append((60 + 110 * math.cos(ang), 0 + 95 * math.sin(ang)))
    prog = eio(seg(lt, 0.2, 2.4))
    nmax = int(prog * len(path))
    nib = (math.cos(math.radians(40)) * 12, math.sin(math.radians(40)) * 12)
    rgba(ctx, (0.06, 0.06, 0.07), a)
    for i in range(1, nmax):
        if i == gap:
            continue
        (x0, y0), (x1, y1) = path[i - 1], path[i]
        ctx.move_to(x0 - nib[0], y0 - nib[1])
        ctx.line_to(x0 + nib[0], y0 + nib[1])
        ctx.line_to(x1 + nib[0], y1 + nib[1])
        ctx.line_to(x1 - nib[0], y1 - nib[1])
        ctx.close_path()
        ctx.fill()
    if prog > 0.98:
        d = eo(seg(lt, 2.4, 2.7))
        ctx.save()
        ctx.translate(60, -60)
        ctx.rotate(math.radians(40))
        ctx.rectangle(-12 * d, -12 * d, 24 * d, 24 * d)
        ctx.restore()
        ctx.fill()
    # kamış kalem
    if nmax > 0 and lt < 2.9:
        px, py = path[min(nmax, len(path) - 1)]
        if prog > 0.98:
            px, py = 60, -60
        ka = a * (1 - seg(lt, 2.6, 2.9))
        ctx.set_line_width(7)
        rgba(ctx, (0.75, 0.55, 0.32), ka)
        ctx.move_to(px + 6, py - 6)
        ctx.line_to(px + 200, py - 260)
        ctx.stroke()
        ctx.set_line_width(3)
        rgba(ctx, (0.06, 0.06, 0.07), ka)
        ctx.move_to(px, py)
        ctx.line_to(px + 16, py - 20)
        ctx.stroke()
    ctx.restore()


def scene_ink(ctx, t, a):
    if a <= 0:
        return
    step = 0 if t < 23.7 else (1 if t < 27.1 else 2)
    step_header(ctx, t, a, step)
    s1 = window(t, 20.3, 23.8, 0.35)
    s2 = window(t, 23.65, 27.2, 0.35)
    s3 = window(t, 27.05, 31, 0.35)
    if s1 > 0:
        ink_step1(ctx, t, a * s1)
    if s2 > 0:
        ctx.save()
        ctx.translate(0, 50)
        ink_step2(ctx, t, a * s2)
        ctx.restore()
    if s3 > 0:
        ink_step3(ctx, t, a * s3)


# ----------------------------------------------------------------- sahne 4: ses
def draw_person(ctx, x, foot, h, c, a):
    r = h * 0.11
    rgba(ctx, c, a)
    ctx.arc(x, foot - h + r, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(h * 0.12)
    ctx.move_to(x, foot - h + 2.6 * r)
    ctx.line_to(x, foot - h * 0.45)
    ctx.stroke()
    ctx.set_line_width(h * 0.07)
    for dx in (-h * 0.03, h * 0.03):
        ctx.move_to(x + dx, foot - h * 0.45)
        ctx.line_to(x + dx, foot)
        ctx.stroke()


def scene_sound(ctx, t, a):
    if a <= 0:
        return
    lt = t - 30.4
    cx, base, R = W / 2, 1230, 300
    dc = (cx, base - 130)
    # kesit
    def section():
        ctx.move_to(cx - 420, base)
        ctx.line_to(cx + 420, base)
        ctx.move_to(cx - 400, base)
        ctx.line_to(cx - 400, base - 230)
        ctx.line_to(cx - R, base - 230)
        ctx.move_to(cx + 400, base)
        ctx.line_to(cx + 400, base - 230)
        ctx.line_to(cx + R, base - 230)
        ctx.move_to(cx - R, dc[1])
        ctx.arc(dc[0], dc[1], R, math.pi, 2 * math.pi)
    ctx.set_line_width(2.2)
    rgba(ctx, WHITE, a * 0.85 * eo(seg(lt, 0, 0.6)))
    section()
    ctx.stroke()
    # kubbedeki küpler
    jars = [math.pi + math.pi * (k + 1) / 9 for k in range(8)]
    src = (cx, base - 150)
    wave_speed = 360
    waves = [lt - 1.1 - k * 0.55 for k in range(8)]
    for ang in jars:
        jx, jy = dc[0] + (R + 18) * math.cos(ang), dc[1] + (R + 18) * math.sin(ang)
        dist = math.dist(src, (jx, jy))
        hit = 0.0
        for w0 in waves:
            if w0 > 0:
                dd = w0 * wave_speed - dist
                if -20 < dd < 160:
                    hit = max(hit, 1 - abs(dd - 40) / 120)
        ja = a * eo(seg(lt, 0.5, 1.0))
        ctx.save()
        ctx.translate(jx, jy)
        ctx.rotate(ang - math.pi / 2)
        ctx.scale(0.11, 0.11)
        jar_path(ctx, 0, -160)
        ctx.close_path()
        ctx.restore()
        rgba(ctx, mix(WHITE, ORANGE, hit), ja)
        ctx.set_line_width(2)
        ctx.stroke()
        if hit > 0:
            glow_dot(ctx, jx, jy, 4, ORANGE, ja * hit)
    # konuşan kişi ve dinleyenler
    draw_person(ctx, cx, base, 140, WHITE, a * eo(seg(lt, 0.3, 0.8)))
    for lx in (cx - 300, cx + 300):
        draw_person(ctx, lx, base, 95, WHITE, a * eo(seg(lt, 0.5, 1.0)) * 0.9)
    # ses dalgaları
    ctx.save()
    ctx.rectangle(0, 0, W, base)
    ctx.clip()
    for w0 in waves:
        if w0 <= 0:
            continue
        r = w0 * wave_speed
        if r > 520:
            continue
        wa = a * (1 - r / 520)

        def arc(r=r):
            ctx.new_sub_path()
            ctx.arc(src[0], src[1], r, math.pi * 1.05, math.pi * 1.95)
        glow_stroke(ctx, arc, ORANGE, 2.2, wa, glow=0.7)
    ctx.restore()
    # dinleyicilere ulaşan dalga
    for sgn in (-1, 1):
        ea = a * seg(lt, 1.8, 2.3)
        if ea <= 0:
            continue
        lx = cx + sgn * 300
        for k in range(3):
            ph = (lt * 1.5 + k / 3) % 1
            ctx.new_sub_path()
            ang0 = -math.pi / 2 - sgn * 0.0
            ctx.arc(lx, base - 85, 30 + ph * 40, -math.pi / 2 - 0.6, -math.pi / 2 + 0.6)
            ctx.set_line_width(2)
            rgba(ctx, ORANGE, ea * (1 - ph))
            ctx.stroke()


# ----------------------------------------------------------------- sahne 6: CTA
def scene_cta(ctx, t, a):
    if a <= 0:
        return
    lt = t - 39.4
    bx, by = 470, 960
    tap = seg(lt, 1.3, 1.6)
    sc = 1 + 0.18 * math.sin(math.pi * tap)
    ctx.save()
    ctx.translate(bx, by)
    ctx.scale(sc, sc)
    ctx.move_to(-30, -42)
    ctx.line_to(30, -42)
    ctx.line_to(30, 42)
    ctx.line_to(0, 18)
    ctx.line_to(-30, 42)
    ctx.close_path()
    ctx.restore()
    rgba(ctx, WHITE, a)
    ctx.fill()
    # kağıt uçak
    px, py = 620, 960
    ctx.set_line_width(3)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(px - 38, py - 4)
    ctx.line_to(px + 40, py - 34)
    ctx.line_to(px + 10, py + 40)
    ctx.line_to(px - 2, py + 8)
    ctx.close_path()
    ctx.move_to(px - 2, py + 8)
    ctx.line_to(px + 40, py - 34)
    rgba(ctx, ORANGE, a)
    ctx.stroke()
    # imleç
    u = eio(seg(lt, 0.3, 1.3))
    mx, my = lerp(760, bx + 8, u), lerp(1200, by + 30, u)
    ctx.move_to(mx, my)
    ctx.line_to(mx, my + 34)
    ctx.line_to(mx + 9, my + 26)
    ctx.line_to(mx + 16, my + 40)
    ctx.line_to(mx + 22, my + 37)
    ctx.line_to(mx + 15, my + 23)
    ctx.line_to(mx + 26, my + 23)
    ctx.close_path()
    rgba(ctx, WHITE, a)
    ctx.fill_preserve()
    rgba(ctx, BG, a)
    ctx.set_line_width(1.5)
    ctx.stroke()
    if tap > 0:
        r = 30 + 60 * tap
        ctx.arc(bx, by, r, 0, 2 * math.pi)
        rgba(ctx, WHITE, a * (1 - tap) * 0.6)
        ctx.set_line_width(2)
        ctx.stroke()


# ----------------------------------------------------------------- kompozisyon
def render_frame(ctx, t):
    paint_bg(ctx)
    a3d = window(t, 4.0, 20.7, 0.45) + window(t, 34.6, 39.6, 0.45)
    draw_grid(ctx, window(t, 3.9, 21, 0.6) + window(t, 34.4, 39.8, 0.6))
    scene_hook(ctx, t, 1 - eio(seg(t, 4.0, 4.4)))
    if a3d > 0:
        scene_3d(ctx, t, a3d)
    scene_ink(ctx, t, window(t, 20.3, 30.7, 0.4))
    scene_sound(ctx, t, window(t, 30.3, 34.9, 0.4))
    scene_cta(ctx, t, eio(seg(t, 39.4, 39.8)))

    # üst bilgi
    if t < 34.6:
        stages = [(4.0, 10.0, 1, "kesit"), (10.0, 20.4, 2, "hava akışı"),
                  (20.4, 30.4, 3, "is → mürekkep"), (30.4, 34.7, 4, "akustik")]
        for s0, s1, n, lab in stages:
            if s0 <= t < s1:
                da = eo(seg(t, 4.0, 4.4))
                draw_dots(ctx, n, da, frac=seg(t, s0, s1))
                la = window(t, s0, s1, 0.3) if n > 1 else eo(seg(t, 4.0, 4.4)) * (1 - eio(seg(t, 9.7, 10.0)))
                stage_label(ctx, n, lab, la)
    else:
        draw_dots(ctx, 4, 1, final=True)

    draw_frame(ctx, eo(seg(t, 4.0, 4.6)) * (1 - eio(seg(t, 39.0, 39.5))))
    draw_captions(ctx, t)
    draw_watermark(ctx)


def main():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    if len(sys.argv) > 2 and sys.argv[1] == "--still":
        for s in sys.argv[2:]:
            render_frame(ctx, float(s))
            surf.write_to_png(f"still_{s}.png")
        return
    out = sys.argv[1] if len(sys.argv) > 1 else "suleymaniye.mp4"
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
