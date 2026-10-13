#!/usr/bin/env python3
"""Generates five fictional 'Lumina Analytics' UI screenshots so you can try the skill end-to-end without any real product.
    python make_sample_screens.py   ->  screenshots/01-dashboard.png ... + logo.png
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)
W, H = 1600, 900
SIDE, TEAL, TEAL2, INK, MUTED, LINE, BG = "#1b1a4b", "#14b8a6", "#f59e0b", "#1f2937", "#6b7280", "#e5e7eb", "#f5f7fb"


def font(size, bold=False):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
              "C:/Windows/Fonts/%s" % ("segoeuib.ttf" if bold else "segoeui.ttf"),
              "/System/Library/Fonts/Supplemental/Arial%s.ttf" % (" Bold" if bold else "")]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def frame(active, title):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 250, H], fill=SIDE)
    d.rounded_rectangle([28, 28, 68, 68], 10, fill=TEAL)
    d.text((82, 34), "Lumina", font=font(28, True), fill="white")
    for i, n in enumerate(["Dashboard", "Reports", "Audiences", "Settings"]):
        y = 130 + i * 62
        if n == active:
            d.rounded_rectangle([14, y - 10, 236, y + 40], 10, fill="#2d2b6b")
        d.text((44, y), n, font=font(22, n == active), fill="white" if n == active else "#a5a3d6")
    d.rectangle([250, 0, W, 76], fill="white")
    d.line([250, 76, W, 76], fill=LINE, width=2)
    d.text((290, 22), title, font=font(30, True), fill=INK)
    d.ellipse([W - 76, 16, W - 28, 64], fill=TEAL2)
    return im, d


def card(d, x, y, w, h):
    d.rounded_rectangle([x, y, x + w, y + h], 14, fill="white", outline=LINE, width=2)


def button(d, x, y, w, h, label, fill=TEAL):
    d.rounded_rectangle([x, y, x + w, y + h], 10, fill=fill)
    f = font(21, True)
    tw = d.textlength(label, font=f)
    d.text((x + (w - tw) / 2, y + h / 2 - 13), label, font=f, fill="white")


def bars(d, x, y, w, h, vals, color=TEAL):
    bw = w / len(vals)
    for i, v in enumerate(vals):
        d.rounded_rectangle([x + i * bw + 8, y + h - v * h, x + (i + 1) * bw - 8, y + h], 6, fill=color)


def s1():
    im, d = frame("Dashboard", "Dashboard")
    for i, (k, v) in enumerate([("Active users", "48.2k"), ("Conversion", "6.4%"), ("Revenue", "$312k")]):
        x = 290 + i * 420
        card(d, x, 110, 390, 150)
        d.text((x + 28, 130), k, font=font(20), fill=MUTED)
        d.text((x + 28, 170), v, font=font(52, True), fill=INK)
    card(d, 290, 290, 800, 540)
    d.text((320, 312), "Weekly active users", font=font(24, True), fill=INK)
    bars(d, 330, 370, 720, 400, [.35, .5, .42, .66, .58, .8, .92])
    card(d, 1120, 290, 450, 540)
    d.text((1150, 312), "Top segments", font=font(24, True), fill=INK)
    for i, (n, p) in enumerate([("Enterprise", .82), ("Growth", .61), ("Startup", .44), ("Free", .27)]):
        y = 380 + i * 100
        d.text((1150, y), n, font=font(21), fill=INK)
        d.rounded_rectangle([1150, y + 38, 1540, y + 54], 8, fill=LINE)
        d.rounded_rectangle([1150, y + 38, 1150 + 390 * p, y + 54], 8, fill=TEAL2)
    return im


def s2():
    im, d = frame("Reports", "Reports")
    button(d, 1330, 14, 240, 48, "+ New report")
    card(d, 290, 110, 1280, 720)
    for i, h in enumerate(["Name", "Owner", "Updated", "Status"]):
        d.text((330 + [0, 560, 800, 1060][i], 140), h, font=font(20, True), fill=MUTED)
    rows = [("Q3 growth review", "Maya", "Today", "Shared"), ("Churn deep dive", "Arun", "Yesterday", "Draft"), ("Board metrics", "Lena", "Mon", "Shared"), ("Campaign ROI", "Tom", "Oct 2", "Draft")]
    for i, r in enumerate(rows):
        y = 200 + i * 90
        d.line([310, y - 14, 1550, y - 14], fill=LINE, width=2)
        for j, t in enumerate(r):
            d.text((330 + [0, 560, 800, 1060][j], y + 10), t, font=font(22, j == 0), fill=INK)
    return im


def s3():
    im, d = frame("Reports", "New report")
    card(d, 290, 110, 1280, 720)
    d.text((330, 140), "Choose a data source", font=font(26, True), fill=INK)
    for i, n in enumerate(["Product events", "CRM", "Billing"]):
        x = 330 + i * 400
        d.rounded_rectangle([x, 200, x + 370, 340], 14, outline=TEAL if i == 0 else LINE, width=4 if i == 0 else 2, fill="#f0fdfa" if i == 0 else "white")
        d.text((x + 28, 250), n, font=font(26, True), fill=INK)
    d.text((330, 390), "Metric", font=font(20), fill=MUTED)
    d.rounded_rectangle([330, 425, 930, 485], 10, outline=LINE, width=2, fill="white")
    d.text((350, 441), "Weekly active users", font=font(22), fill=INK)
    d.text((330, 530), "Date range", font=font(20), fill=MUTED)
    d.rounded_rectangle([330, 565, 930, 625], 10, outline=LINE, width=2, fill="white")
    d.text((350, 581), "Last 30 days", font=font(22), fill=INK)
    button(d, 1250, 740, 290, 60, "Generate report")
    return im


def s4():
    im, d = frame("Reports", "Q3 growth review")
    card(d, 290, 110, 1280, 400)
    d.text((320, 130), "Weekly active users - last 30 days", font=font(24, True), fill=INK)
    bars(d, 330, 190, 1180, 290, [.3, .36, .45, .4, .52, .6, .58, .7, .66, .8, .86, .95], TEAL)
    card(d, 290, 540, 620, 290)
    d.text((320, 560), "AI summary", font=font(24, True), fill=INK)
    for i, t in enumerate(["Usage grew 28% month over month.", "Enterprise drove most of the lift.", "Retention held steady at 91%."]):
        d.text((320, 620 + i * 54), "• " + t, font=font(21), fill=INK)
    card(d, 940, 540, 630, 290)
    d.text((970, 560), "Anomalies", font=font(24, True), fill=INK)
    d.rounded_rectangle([970, 620, 1540, 700], 12, fill="#fff7ed", outline=TEAL2, width=2)
    d.text((992, 645), "Spike on Oct 8: +42% sign-ups", font=font(21, True), fill="#92400e")
    return im


def s5():
    im, d = frame("Reports", "Q3 growth review")
    card(d, 290, 110, 1280, 400)
    bars(d, 330, 180, 1180, 300, [.3, .36, .45, .4, .52, .6, .58, .7, .66, .8, .86, .95], TEAL)
    d.rounded_rectangle([520, 250, 1100, 700], 18, fill="white", outline=LINE, width=3)
    d.text((560, 280), "Share report", font=font(28, True), fill=INK)
    d.text((560, 350), "Invite people", font=font(20), fill=MUTED)
    d.rounded_rectangle([560, 385, 1060, 445], 10, outline=LINE, width=2)
    d.text((580, 401), "team@company.com", font=font(22), fill=INK)
    d.text((560, 480), "Access", font=font(20), fill=MUTED)
    d.rounded_rectangle([560, 515, 1060, 575], 10, outline=LINE, width=2)
    d.text((580, 531), "Can view", font=font(22), fill=INK)
    button(d, 800, 610, 260, 60, "Send invite")
    return im


for i, (n, fn) in enumerate([("dashboard", s1), ("reports", s2), ("new-report", s3), ("report-detail", s4), ("share", s5)], 1):
    fn().save(OUT / f"{i:02d}-{n}.png")

logo = Image.new("RGBA", (360, 100), (0, 0, 0, 0))
ld = ImageDraw.Draw(logo)
ld.rounded_rectangle([6, 8, 86, 88], 20, fill=TEAL)
ld.text((26, 22), "L", font=font(52, True), fill="white")
ld.text((106, 26), "Lumina", font=font(48, True), fill=SIDE)
logo.save(Path(__file__).parent / "logo.png")
print("wrote", OUT, "and logo.png")
