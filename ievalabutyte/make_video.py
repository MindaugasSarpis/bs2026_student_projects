from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1280, 720
FPS = 4

def get_font(size):
    for p in ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

fb = get_font(42)
fm = get_font(24)
fs = get_font(17)
fxs = get_font(15)

GREEN = (46, 204, 113)
YELLOW = (241, 196, 15)
WHITE = (255, 255, 255)
LIGHT = (200, 210, 220)
GRAY = (130, 140, 150)
ACCENT_BG = (18, 25, 50)

def gradient_bg(colors):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    seg_h = H // (len(colors) - 1)
    for s in range(len(colors) - 1):
        r1, g1, b1 = colors[s]
        r2, g2, b2 = colors[s+1]
        for y in range(seg_h):
            t = y / seg_h
            r = int(r1 + (r2-r1)*t)
            g = int(g1 + (g2-g1)*t)
            b = int(b1 + (b2-b1)*t)
            d.line([(0, s*seg_h+y), (W, s*seg_h+y)], fill=(r, g, b))
    return img

def add_dots(img, count=40, seed=42):
    import random
    random.seed(seed)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = random.randint(0,W), random.randint(0,H)
        s = random.randint(1,3)
        a = random.randint(40,120)
        d.ellipse([x-s,y-s,x+s,y+s], fill=(a, a+30, a+60))
    return img

def accent_line(d, y, width=400):
    x0 = (W - width) // 2
    for x in range(width):
        t = x / width
        d.line([(x0+x, y), (x0+x, y+2)], fill=(30, int(46+(204-46)*t), int(80+(113-80)*t)))

def center_text(d, text, y, font, fill):
    bbox = d.textbbox((0,0), text, font=font)
    d.text(((W - (bbox[2]-bbox[0]))//2, y), text, font=font, fill=fill)

def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = draw.textbbox((0,0), test, font=font)
        if bbox[2]-bbox[0] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def fade_color(color, fade):
    return tuple(int(v * fade) for v in color)

def build_title():
    bg = add_dots(gradient_bg([(5,5,20),(15,30,70),(5,15,40)]), 60, 1)
    elems = [(12,"Export-as-a-Service",180,fb,WHITE),(16,"Market Players Analysis",240,fb,WHITE),(20,"line",310,None,None),(24,"Ieva Labutyte",330,fm,LIGHT),(28,"BS2026 Data Analysis Course | April 2026",370,fs,GRAY),(32,"17 companies | 7 countries | 5 service types",420,fs,GREEN)]
    frames = []
    for f in range(FPS*6):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        for appear,text,y,font,fill in elems:
            if f >= appear:
                fade = min(1.0,(f-appear)/4)
                if text == "line": accent_line(d,y,int(400*fade))
                else: center_text(d,text,y,font,fade_color(fill,fade))
        frames.append(img)
    return frames

def build_chart(chart_path, title, insights):
    bg = add_dots(gradient_bg([(8,8,25),(12,25,55),(8,12,30)]), 30, hash(title)%100)
    chart_img = None
    if os.path.exists(chart_path):
        chart_img = Image.open(chart_path).convert("RGB").resize((660,400), Image.LANCZOS)
    frames = []
    px = 700
    for f in range(FPS*7):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        tf = min(1.0, f/4)
        d.rectangle([0,8,W,55], fill=fade_color((20,35,70),tf))
        center_text(d,title,16,fm,fade_color(WHITE,tf))
        if chart_img and f >= 3:
            cp = min(1.0,(f-3)/6)
            xoff = int(-680+700*cp)
            temp = Image.blend(Image.new("RGB",chart_img.size,(8,8,25)),chart_img,cp) if cp<1 else chart_img
            img.paste(temp,(max(20,xoff),70))
        if f >= 6:
            pf = min(1.0,(f-6)/4)
            d.rectangle([px,70,W-15,490], fill=fade_color(ACCENT_BG,pf), outline=fade_color(GREEN,pf), width=1)
            d.rectangle([px,70,W-15,105], fill=fade_color((25,40,65),pf))
            bbox = d.textbbox((0,0),"Key Insights",font=fs)
            tw = bbox[2]-bbox[0]
            d.text((px+((W-15-px)-tw)//2,77),"Key Insights",font=fs,fill=fade_color(GREEN,pf))
        y = 120
        for i,insight in enumerate(insights):
            appear = 10+i*4
            lines = wrap_text(insight,fxs,(W-15-px-30),d)
            if f >= appear:
                ifade = min(1.0,(f-appear)/3)
                for j,line in enumerate(lines):
                    if j==0: d.text((px+12,y),">",font=fxs,fill=fade_color(GREEN,ifade))
                    d.text((px+28,y),line,font=fxs,fill=fade_color(LIGHT,ifade))
                    y += 20
            else:
                y += len(lines)*20
            y += 8
        frames.append(img)
    return frames

def build_summary():
    bg = add_dots(gradient_bg([(8,8,25),(20,35,65),(8,15,35)]), 50, 99)
    items = [("Market is split into two camps:",WHITE,8),("   Digital-first platforms (Global-e, Zonos, Flow)",GREEN,12),("   Legacy logistics giants gone digital (DHL, FedEx)",GREEN,16),("",WHITE,0),("USA leads (41%), but Israel, Germany, and UAE",WHITE,22),("are strong innovation hubs",WHITE,24),("",WHITE,0),("Older companies = larger revenue, but new entrants",WHITE,30),("are growing fast in niche segments",WHITE,32),("",WHITE,0),("Cross-border eCommerce is the fastest-growing",WHITE,38),("service type with 5 out of 17 companies",WHITE,40),("",WHITE,0),("Revenue gap is massive: $10M to $45B",YELLOW,46),("Room for mid-market disruption",YELLOW,48)]
    frames = []
    for f in range(FPS*8):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        if f >= 2:
            tf = min(1.0,(f-2)/4)
            center_text(d,"Key Takeaways",40,fb,fade_color(WHITE,tf))
            accent_line(d,95,int(400*tf))
        y = 130
        for text,color,appear in items:
            if text and f >= appear: d.text((200,y),text,font=fs,fill=fade_color(color,min(1.0,(f-appear)/3)))
            y += 28
        frames.append(img)
    return frames

def build_closing():
    bg = add_dots(gradient_bg([(5,5,20),(15,30,70),(5,15,40)]), 60, 42)
    frames = []
    for f in range(FPS*5):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        if f>=2: center_text(d,"Thank You",220,fb,fade_color(WHITE,min(1.0,(f-2)/4)))
        if f>=6: accent_line(d,285,int(400*min(1.0,(f-6)/4)))
        if f>=8: center_text(d,"Ieva Labutyte | BS2026",305,fm,fade_color(LIGHT,min(1.0,(f-8)/4)))
        if f>=12: center_text(d,"Python | pandas | matplotlib | seaborn | Jupyter",355,fs,fade_color(GREEN,min(1.0,(f-12)/4)))
        if f>=16: center_text(d,"github.com/labutyteieva-jpg/Projectforbs2026",405,fxs,fade_color(GRAY,min(1.0,(f-16)/4)))
        frames.append(img)
    return frames

print("Building title...")
title_f = build_title()
charts = [("chart_service_types.png","Companies by Service Type",["Cross-border eCommerce leads with 5 companies (29%)","Freight forwarding second with 4 companies","Freight marketplace emerging with 3 players","Market consolidating around 3 core models"]),("chart_countries.png","EaaS Companies by Country",["USA dominates with 7 of 17 companies (41%)","Israel punches above its weight (3 companies)","Germany hosts 3 companies, mostly freight","UAE emerging as logistics hub","No Asian companies in top 17 yet"]),("chart_revenue.png","Revenue Comparison (Log Scale)",["DHL leads at $45B, 90x larger than median","FedEx ($25B) and Aramex ($5B) follow","Flexport ($2.2B) bridges legacy and startups","Most startups cluster at $10M-$100M","Log scale needed: massive revenue gap"]),("chart_company_sizes.png","Company Size Distribution",["Evenly split: 35% Small, 35% Medium, 29% Large","No single size dominates the market","Small = niche digital solutions","Large = legacy logistics companies"]),("chart_company_age.png","Company Age Analysis",["Pitney Bowes oldest at 106 years","DHL (57) and FedEx (55) are legacy giants","Most digital-first companies post-2005","Ship4wd (2022) is newest entrant","Average: 32 years, median much lower"]),("chart_correlation.png","Feature Correlations",["Age and size: strong (r=0.66)","Size and revenue: moderate (r=0.54)","Age and revenue: moderate (r=0.50)","Older companies had time to grow","Young companies compete in niches"])]
chart_f = []
for i,(cp,t,ins) in enumerate(charts):
    print(f"Building chart {i+1}/6: {t}...")
    chart_f.append(build_chart(cp,t,ins))
print("Building summary...")
summary_f = build_summary()
print("Building closing...")
closing_f = build_closing()
def make_fade(f1,f2,n=4):
    return [Image.blend(f1[-1],f2[0],(i+1)/(n+1)) for i in range(n)]
print("Adding transitions...")
all_f = list(title_f)
all_f += make_fade(title_f,chart_f[0])
for i,cf in enumerate(chart_f):
    all_f += list(cf)
    if i<len(chart_f)-1: all_f += make_fade(cf,chart_f[i+1])
all_f += make_fade(chart_f[-1],summary_f)
all_f += list(summary_f)
all_f += make_fade(summary_f,closing_f)
all_f += list(closing_f)
print(f"Saving GIF ({len(all_f)} frames)...")
all_f[0].save("project_video.gif",save_all=True,append_images=all_f[1:],duration=250,loop=0)
print(f"Done! ~{len(all_f)*0.25:.0f} seconds")
