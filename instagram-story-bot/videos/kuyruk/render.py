"""Anne babanla kalan gerçek zaman (Kuyruk Sonu) — 9:16 minimal çizim videosu.

Stil ve yardımcılar ../suleymaniye/render.py ile ortak.

Kullanım:
  python3 render.py              -> kuyruk.mp4
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
             "draw_dots draw_grid WHITE GREY DARK ORANGE").split()
globals().update({k: getattr(base, k) for k in from_base})

DUR = 39.6
AMBER = (1.0, 0.78, 0.30)
GREEN = (0.20, 0.78, 0.36)
CTA_T = 35.8


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
    (0.10, 2.00, T("Anne babanla geçireceğin yüz yüze zamanın *%90'ı..."), 0.08, 46),
    (2.05, 4.15, T("...daha *18 *yaşına gelmeden ^bitti."), 0.10, 48),
    (4.40, 7.20, T("Her nokta, birlikte geçireceğin zamanın *binde *biri."), 0.09, 44),
    (7.30, 10.0, T("Toplam *1000 nokta. Çok gibi, değil mi?"), 0.10, 44),
    (10.2, 13.0, T("Okul, ev, sofra... *18 *yıl hep birlikteydiniz."), 0.09, 44),
    (13.1, 16.0, T("Geriye kalan: ^100 ^nokta."), 0.12, 50),
    (16.3, 19.0, T("Yılda sadece *bayramda *5 *gün görüyorsan..."), 0.10, 44),
    (19.1, 22.5, T("...her bayram birkaç nokta daha *söner."), 0.10, 44),
    (22.6, 26.0, T("Ve sen bunu *fark *etmezsin."), 0.12, 46),
    (26.3, 28.9, T("Ama hâlâ *yanan noktalar var."), 0.10, 44),
    (29.0, 32.8, T("Bugün o noktalardan *birini ^çoğalt."), 0.12, 48),
    (33.0, 35.6, T("Mesaj değil. *Sesini *duysunlar."), 0.11, 46),
    (35.8, 39.6, T("*Kaydet, bir *kardeşine gönder."), 0.11, 46),
]


# ------------------------------------------------------------------ noktalar
COLS, ROWS, SP = 25, 40, 21
GX0 = W / 2 - (COLS - 1) * SP / 2
GY0 = 505
GRID = [(GX0 + (i % COLS) * SP, GY0 + (i // COLS) * SP) for i in range(1000)]
LAST = list(range(900, 1000))  # 18 yaştan sonraki 100 nokta

# 10x10 yakın plan yerleşimi
ZSP = 58
ZGRID = [(W / 2 + ((k % 10) - 4.5) * ZSP, 900 + ((k // 10) - 4.5) * ZSP) for k in range(100)]
# S4'te küçülüp yukarı kayan yerleşim
SGRID = [(W / 2 + ((k % 10) - 4.5) * 40, 800 + ((k // 10) - 4.5) * 40) for k in range(100)]

_r = random.Random(12)
OFF_ORDER = list(range(100))
_r.shuffle(OFF_ORDER)
YEAR_T0, YEAR_DT, PER_YEAR, YEARS = 18.6, 0.55, 5, 13
OFF_TIME = {}
for y in range(YEARS):
    for j in range(PER_YEAR):
        OFF_TIME[OFF_ORDER[y * PER_YEAR + j]] = YEAR_T0 + y * YEAR_DT + j * 0.07
RELIT = [OFF_ORDER[YEARS * PER_YEAR - 1 - k] for k in range(5)]  # en son sönenler geri yanar
RELIT_T = {k: 30.0 + i * 0.32 for i, k in enumerate(RELIT)}


def ring(ctx, x, y, r, c, a, w=1.4):
    ctx.new_path()
    ctx.set_line_width(w)
    rgba(ctx, c, a)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.stroke()


def scene_dots(ctx, t, a):
    if a <= 0:
        return
    # 1000 nokta (S1-S2)
    a_all = a * (1 - eio(seg(t, 15.6, 16.4)))
    if a_all > 0:
        for i, (x, y) in enumerate(GRID):
            appear = eo(seg(t, 4.2 + (i // COLS) * 0.045 + (i % COLS) * 0.004, 4.6 + (i // COLS) * 0.045))
            if appear <= 0:
                continue
            row = i // COLS
            if i < 900:
                d = eio(seg(t, 11.0 + row * 0.022, 11.25 + row * 0.022))
                c = mix(WHITE, (0.16, 0.17, 0.2), d)
                rgba(ctx, c, a_all * appear * lerp(0.85, 1, d))
                ctx.arc(x, y, 4.2 * lerp(1, 0.8, d), 0, 2 * math.pi)
                ctx.fill()
            else:
                g = eo(seg(t, 12.2, 12.8))
                if t < 16.0:
                    if g > 0:
                        glow_dot(ctx, x, y, 4.2, AMBER, a_all * appear * g)
                    rgba(ctx, WHITE, a_all * appear * (1 - g))
                    ctx.arc(x, y, 4.2, 0, 2 * math.pi)
                    ctx.fill()
        # "18 yaş" sınırı
        la = a_all * eo(seg(t, 12.4, 12.9))
        if la > 0:
            yb = GY0 + 35.5 * SP
            ctx.set_line_width(1.5)
            rgba(ctx, AMBER, la * 0.7)
            ctx.set_dash([6, 6])
            ctx.move_to(GX0 - 30, yb)
            ctx.line_to(GX0 + (COLS - 1) * SP + 30, yb)
            ctx.stroke()
            ctx.set_dash([])
            font(ctx, 22, "b")
            ctx.move_to(GX0 + (COLS - 1) * SP + 40, yb + 8)
            rgba(ctx, AMBER, la)
            ctx.show_text("18 yaş")
            font(ctx, 22, "r")
            ctx.move_to(GX0 + (COLS - 1) * SP + 40, GY0 + 15 * SP)
            rgba(ctx, GREY, la)
            ctx.show_text("geçti")

    # 100 nokta (S2 sonu - S5)
    if t >= 15.6:
        mv = eio(seg(t, 15.8, 17.2))
        sh = eio(seg(t, 26.2, 27.4))
        for k, i in enumerate(LAST):
            x0, y0 = GRID[i]
            zx, zy = ZGRID[k]
            sx, sy = SGRID[k]
            x = lerp(lerp(x0, zx, mv), sx, sh)
            y = lerp(lerp(y0, zy, mv), sy, sh)
            r = lerp(lerp(4.2, 11, mv), 8, sh)
            off = OFF_TIME.get(k)
            lit = 1.0
            if off is not None and t > off:
                u = seg(t, off, off + 0.35)
                flick = 0.5 + 0.5 * math.sin((t - off) * 60)
                lit = (1 - u) * (flick if u < 1 else 0)
            rel = RELIT_T.get(k)
            pop = 0.0
            if rel is not None and t > rel:
                pop = seg(t, rel, rel + 0.35)
                lit = max(lit, eo(pop))
            if lit < 1:
                ring(ctx, x, y, r, (0.35, 0.36, 0.4), a * (1 - lit) * 0.9)
            if lit > 0:
                rr = r * (1 + 0.5 * math.sin(math.pi * pop)) if pop > 0 else r
                glow_dot(ctx, x, y, rr, AMBER, a * lit)
        # yıl / kalan sayaçları
        ca = a * window(t, 18.3, 26.4, 0.3)
        if ca > 0:
            yrs = int(clamp((t - YEAR_T0) / YEAR_DT + 1, 0, YEARS)) if t > YEAR_T0 else 0
            left = 100 - sum(1 for k, ot in OFF_TIME.items() if t > ot + 0.2)
            font(ctx, 26, "r")
            rgba(ctx, GREY, ca)
            ctx.move_to(ZGRID[0][0] - 12, 590)
            ctx.show_text(f"+{yrs} yıl")
            s = f"kalan: {left}"
            font(ctx, 26, "b")
            ctx.move_to(ZGRID[9][0] + 12 - ctx.text_extents(s).x_advance, 590)
            rgba(ctx, AMBER, ca)
            ctx.show_text(s)
        if t > 29.9:
            left = 35 + sum(1 for k in RELIT if t > RELIT_T[k] + 0.1)
            text_c(ctx, f"{left}", W / 2, 1090, 40, AMBER, a * eo(seg(t, 29.9, 30.2)), "b")


# ------------------------------------------------------------------ telefon
CALL_ICON = ("M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57"
             ".55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 "
             "0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z")


def svg_path(ctx, d):
    """M/L/H/V/C/Z (büyük-küçük) destekli küçük SVG yol çizici."""
    import re
    toks = re.findall(r"[MLHVCZmlhvcz]|-?(?:\d+\.?\d*|\.\d+)", d)
    i, cmd, x, y = 0, None, 0.0, 0.0
    need = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "z": 0}
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "zZ":
                ctx.close_path()
                continue
        n = need[cmd.lower()]
        v = [float(q) for q in toks[i:i + n]]
        i += n
        rel = cmd.islower()
        c = cmd.lower()
        if c in "ml":
            x, y = (x + v[0], y + v[1]) if rel else (v[0], v[1])
            (ctx.move_to if c == "m" else ctx.line_to)(x, y)
            if c == "m":
                cmd = "l" if rel else "L"
        elif c == "h":
            x = x + v[0] if rel else v[0]
            ctx.line_to(x, y)
        elif c == "v":
            y = y + v[0] if rel else v[0]
            ctx.line_to(x, y)
        elif c == "c":
            if rel:
                v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y, v[4] + x, v[5] + y]
            ctx.curve_to(*v)
            x, y = v[4], v[5]


def scene_call(ctx, t, a):
    if a <= 0:
        return
    bx, by, R = W / 2, 1210, 62
    lt = t - 26.8
    tap = seg(lt, 2.1, 2.4)
    sc = eo(seg(lt, 0, 0.4)) * (1 - 0.12 * math.sin(math.pi * tap))
    # nabız halkaları
    for k in range(2):
        ph = (lt * 0.8 + k * 0.5) % 1
        ring(ctx, bx, by, R * (1 + ph * 0.8), GREEN, a * (1 - ph) * 0.5, 2)
    ctx.save()
    ctx.translate(bx, by)
    ctx.scale(sc, sc)
    g = cairo.RadialGradient(0, 0, R * 0.6, 0, 0, R * 2.2)
    g.add_color_stop_rgba(0, GREEN[0], GREEN[1], GREEN[2], 0.35 * a)
    g.add_color_stop_rgba(1, GREEN[0], GREEN[1], GREEN[2], 0)
    ctx.set_source(g)
    ctx.arc(0, 0, R * 2.2, 0, 2 * math.pi)
    ctx.fill()
    rgba(ctx, GREEN, a)
    ctx.arc(0, 0, R, 0, 2 * math.pi)
    ctx.fill()
    # ahize (24x24 arama ikonu yolu)
    ctx.scale(2.6, 2.6)
    ctx.translate(-12, -12)
    svg_path(ctx, CALL_ICON)
    rgba(ctx, WHITE, a)
    ctx.fill()
    ctx.restore()
    if tap > 0:
        ring(ctx, bx, by, R + 80 * tap, WHITE, a * (1 - tap) * 0.7, 2)
    # "arıyor..." yazısı
    if lt > 2.4:
        dots = "." * (1 + int((lt * 3) % 3))
        text_c(ctx, "aranıyor" + dots, bx, by + R + 50, 24, GREEN, a * eo(seg(lt, 2.4, 2.7)))
    # imleç
    u = eio(seg(lt, 0.8, 2.1))
    mx, my = lerp(820, bx + 10, u), lerp(1330, by + 14, u)
    ma = a * (1 - seg(lt, 3.0, 3.4))
    ctx.move_to(mx, my)
    ctx.line_to(mx, my + 34)
    ctx.line_to(mx + 9, my + 26)
    ctx.line_to(mx + 16, my + 40)
    ctx.line_to(mx + 22, my + 37)
    ctx.line_to(mx + 15, my + 23)
    ctx.line_to(mx + 26, my + 23)
    ctx.close_path()
    rgba(ctx, WHITE, ma)
    ctx.fill_preserve()
    rgba(ctx, base.BG, ma)
    ctx.set_line_width(1.5)
    ctx.stroke()


# ------------------------------------------------------------------ kanca
def scene_hook(ctx, t, a):
    if a <= 0:
        return
    p = eio(seg(t, 0.2, 2.0))
    n = int(round(90 * p))
    font(ctx, 230, "t")
    s = str(n)
    w = ctx.text_extents(s).x_advance
    ctx.move_to(W / 2 - w / 2 - 30, 840)
    rgba(ctx, WHITE, a)
    ctx.show_text(s)
    font(ctx, 90, "t")
    ctx.move_to(W / 2 + w / 2 - 20, 840)
    rgba(ctx, AMBER, a)
    ctx.show_text("%")
    # ömür çubuğu
    x0, x1, y = 150, 930, 1010
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(10)
    rgba(ctx, WHITE, a * 0.14)
    ctx.move_to(x0, y)
    ctx.line_to(x1, y)
    ctx.stroke()
    fx = lerp(x0, x1, 0.9 * p)
    if p > 0:
        rgba(ctx, mix(WHITE, AMBER, 0.15), a * 0.55)
        ctx.move_to(x0, y)
        ctx.line_to(fx, y)
        ctx.stroke()
    # kalan %10 nabız gibi parlar
    rest = eo(seg(t, 2.0, 2.4))
    if rest > 0:
        pl = 0.75 + 0.25 * math.sin(t * 6)
        def seg_path():
            ctx.move_to(lerp(x0, x1, 0.9) + 8, y)
            ctx.line_to(x1, y)
        glow_stroke(ctx, seg_path, AMBER, 10, a * rest * pl, glow=1.2)
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    text_c(ctx, "doğum", x0, y + 50, 22, GREY, a)
    text_c(ctx, "18 yaş", lerp(x0, x1, 0.9) - 20, y + 50, 22, WHITE, a * eo(seg(t, 1.6, 2.0)), "b")
    text_c(ctx, "kalan", x1, y - 30, 22, AMBER, a * rest, "b")
    # yürüyen çöp adam
    px = lerp(x0, x1, 0.9 * p)
    base.draw_person(ctx, px, y - 14, 70, WHITE, a * 0.9)


def render_frame(ctx, t):
    base.paint_bg(ctx)
    draw_grid(ctx, 0.6 * window(t, 3.9, 35.6, 0.6))
    scene_hook(ctx, t, 1 - eio(seg(t, 4.0, 4.4)))
    scene_dots(ctx, t, window(t, 4.0, 35.4, 0.45))
    scene_call(ctx, t, window(t, 26.8, 35.4, 0.4))
    base.scene_cta(ctx, t + (39.4 - CTA_T - 0.2), eio(seg(t, CTA_T - 0.2, CTA_T + 0.2)))
    if t < 33.0:
        stages = [(4.0, 10.1, 1, "tüm zaman"), (10.1, 16.2, 2, "18 yaş"),
                  (16.2, 26.2, 3, "kalan"), (26.2, 33.0, 4, "bugün")]
        for s0, s1, n, lab in stages:
            if s0 <= t < s1:
                draw_dots(ctx, n, eo(seg(t, 4.0, 4.4)), frac=seg(t, s0, s1))
                la = window(t, s0, s1, 0.3) if n > 1 else eo(seg(t, 4.0, 4.4)) * (1 - eio(seg(t, 9.8, 10.1)))
                base.stage_label(ctx, n, lab, la)
    else:
        draw_dots(ctx, 4, 1, final=True)
    base.draw_frame(ctx, eo(seg(t, 4.0, 4.6)) * (1 - eio(seg(t, CTA_T - 0.6, CTA_T - 0.1))))
    base.draw_captions(ctx, t)
    base.draw_watermark(ctx)


def main():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    if len(sys.argv) > 2 and sys.argv[1] == "--still":
        for s in sys.argv[2:]:
            render_frame(ctx, float(s))
            surf.write_to_png(f"still_{s}.png")
        return
    out = sys.argv[1] if len(sys.argv) > 1 else "kuyruk.mp4"
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
