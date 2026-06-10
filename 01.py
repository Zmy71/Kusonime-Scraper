# Zero.py - Scraping Kusonime.com
# Copyright (c) 2026 JuanKarya
# 
# This project is licensed under the MIT License.
# See the LICENSE file in the project root for details.

import sys, time, re, base64, os
from urllib.parse import urlparse, parse_qs, quote
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://kusonime.com"
SESSION  = requests.Session()

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"
    BG_BLUE    = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN    = "\033[46m"
    BG_BLACK   = "\033[40m"

def c(color, text): return f"{color}{text}{C.RESET}"
def bold(text):     return c(C.BOLD, text)

W = min(os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80, 80)

def bar(char="─", color=C.GRAY):
    print(c(color, char * W))

def header_bar(text, bg=C.BG_BLUE, fg=C.WHITE):
    pad   = W - len(text) - 4
    left  = pad // 2
    right = pad - left
    print(f"{bg}{fg}{C.BOLD}  {'─'*left} {text} {'─'*right}  {C.RESET}")

def section(title, icon="", color=C.CYAN):
    print()
    print(c(color + C.BOLD, f"  {icon}  {title}"))
    bar("─", color)

def get_soup(url: str, delay=1.2):
    try:
        time.sleep(delay)
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200:
            print(c(C.RED, f"  ✗ HTTP {r.status_code}"))
            return None
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(c(C.RED, f"  ✗ Error: {e}"))
        return None

def decode_url(raw: str) -> str:
    if not raw: return raw
    try:
        qs = parse_qs(urlparse(raw).query)
        candidate = None
        for key in ("url", "u", "link", "l", "file"):
            if key in qs:
                candidate = qs[key][0]; break
        if not candidate:
            seg = raw.strip()
            if re.match(r'^[A-Za-z0-9+/\-_]{20,}={0,3}$', seg):
                candidate = seg
        if candidate:
            candidate = candidate.replace('-','+').replace('_','/')
            candidate += '=' * ((4 - len(candidate) % 4) % 4)
            decoded = base64.b64decode(candidate).decode('utf-8')
            if decoded.startswith('http'): return decoded
    except Exception:
        pass
    return raw

def parse_detpost(posts, start_idx=1):
    entries = []
    for idx, post in enumerate(posts, start_idx):
        title_a = post.select_one("h2.episodeye a") or post.select_one("div.content h2 a")
        if not title_a: continue
        title    = title_a.get_text(strip=True)
        post_url = title_a.get("href", "")
        if not title or not post_url: continue
        img    = post.select_one("div.thumb img")
        thumb  = (img.get("data-src") or img.get("src") or "") if img else ""
        genres = [a.get_text(strip=True) for a in post.select("a[rel='tag']")]
        released = "-"
        for p in post.select("div.content p"):
            txt = p.get_text(strip=True)
            if "released" in txt.lower() or "fa-clock" in str(p):
                released = re.sub(r"(?i)released\s*on\s*:?\s*", "", txt).strip()
                break
        entries.append({"no": idx, "title": title, "url": post_url,
                        "thumb": thumb, "genres": genres, "released": released})
    return entries

def scrape_latest(page=1):
    url  = BASE_URL if page == 1 else f"{BASE_URL}/page/{page}/"
    soup = get_soup(url)
    if not soup: return []
    return parse_detpost(soup.select("div.detpost"))

def search_anime(query: str):
    soup = get_soup(f"{BASE_URL}/?s={quote(query)}")
    if not soup: return []
    return parse_detpost(soup.select("div.detpost"))

def scrape_detail(url: str) -> dict:
    soup = get_soup(url)
    if not soup: return {}
    h1    = soup.select_one("h1.jdlz") or soup.select_one("h1")
    title = h1.get_text(strip=True) if h1 else ""
    if not title: return {}
    img   = soup.select_one("div.post-thumb img") or soup.select_one("div.venser img")
    thumb = (img.get("data-src") or img.get("src") or "") if img else ""
    info  = {k: "-" for k in ["japanese","season","producers","type",
                                "status","total_eps","score","duration","released_on"]}
    info["genres"] = []
    info_div = soup.select_one("div.info")
    if info_div:
        for p in info_div.select("p"):
            b = p.select_one("b")
            if not b: continue
            label = b.get_text(strip=True).rstrip(":").strip().lower()
            val   = re.sub(rf"^{re.escape(b.get_text(strip=True))}\s*:?\s*",
                           "", p.get_text(" ", strip=True)).strip()
            links = [a.get_text(strip=True) for a in p.select("a")]
            if "japanese" in label or "alternate" in label: info["japanese"]    = val
            elif "genre"   in label: info["genres"]      = links or [v.strip() for v in val.split(",") if v.strip()]
            elif "season"  in label: info["season"]      = ", ".join(links) if links else val
            elif "producer" in label or "studio" in label: info["producers"]   = ", ".join(links) if links else val
            elif label in ("type","tipe"):                  info["type"]        = val
            elif "status"  in label:                        info["status"]      = val
            elif "total episode" in label or "total ep" in label: info["total_eps"] = val
            elif "score"   in label or "rating" in label:  info["score"]       = val
            elif "duration" in label or "durasi" in label: info["duration"]    = val
            elif "released" in label or "aired" in label or "tayang" in label: info["released_on"] = val
    parts = []
    lexot = soup.select_one("div.lexot")
    if lexot:
        for p in lexot.select("p"):
            if p.find_parent("div", class_="info"): continue
            txt = p.get_text(strip=True)
            if txt and len(txt) > 20: parts.append(txt)
    synopsis = " ".join(parts).strip() or "-"
    download = {}
    dlbodz   = soup.select_one("div.dlbodz")
    if dlbodz:
        for grp in dlbodz.select("div.smokeddlrh"):
            for row in grp.select("div.smokeurlrh"):
                strong  = row.select_one("strong")
                res     = strong.get_text(strip=True) if strong else "Unknown"
                mirrors = []
                for a in row.select("a"):
                    href = a.get("href", "").strip()
                    mirrors.append({"mirror": a.get_text(strip=True),
                                    "url": decode_url(href), "url_raw": href})
                if mirrors: download[res] = mirrors
    return {"title": title, "url": url, "thumbnail": thumb,
            "japanese": info["japanese"], "genres": info["genres"],
            "season": info["season"], "producers": info["producers"],
            "type": info["type"], "status": info["status"],
            "total_eps": info["total_eps"], "score": info["score"],
            "duration": info["duration"], "released_on": info["released_on"],
            "synopsis": synopsis, "download": download}

GENRE_COLORS = {
    "Action": C.RED, "Adventure": C.YELLOW, "Comedy": C.GREEN,
    "Drama": C.CYAN, "Fantasy": C.MAGENTA, "Horror": C.RED,
    "Romance": C.MAGENTA, "Sci-Fi": C.BLUE, "Thriller": C.RED,
    "Mystery": C.CYAN, "Music": C.GREEN, "Sports": C.YELLOW,
    "Shounen": C.YELLOW, "Seinen": C.BLUE, "Slice of Life": C.GREEN,
}

def genre_badge(g):
    color = GENRE_COLORS.get(g, C.GRAY)
    return f"{color}[{g}]{C.RESET}"

def score_color(score_str):
    try:
        s = float(re.search(r"[\d.]+", score_str).group())
        if s >= 8.5: return C.GREEN + C.BOLD
        if s >= 7.0: return C.YELLOW
        return C.RED
    except: return C.WHITE

def status_badge(status):
    sl = status.lower()
    if "completed" in sl or "selesai" in sl:
        return c(C.GREEN + C.BOLD, f"● {status}")
    if "ongoing" in sl or "berjalan" in sl:
        return c(C.YELLOW + C.BOLD, f"◉ {status}")
    return c(C.GRAY, f"○ {status}")

def truncate(text, max_len):
    return text if len(text) <= max_len else text[:max_len-3] + "..."

def print_latest(entries):
    print()
    header_bar("🆕  UPLOAD TERBARU", C.BG_CYAN, C.WHITE)
    print()
    for e in entries:
        no_str = c(C.CYAN + C.BOLD, f"  [{e['no']:>2}]")
        title  = c(C.WHITE + C.BOLD, truncate(e['title'], W - 10))
        genres = "  ".join(genre_badge(g) for g in e['genres']) if e['genres'] else c(C.GRAY, "-")
        rel    = c(C.GRAY, f"🕐 {e['released']}")
        print(f"{no_str} {title}")
        print(f"       {genres}")
        print(f"       {rel}")
        print(c(C.GRAY, "  " + "·"*( W - 3)))
    print()

def print_search(entries, query=""):
    print()
    header_bar(f"🔍  HASIL: \"{query}\"", C.BG_MAGENTA, C.WHITE)
    print()
    if not entries:
        print(c(C.YELLOW, "  ⚠  Tidak ada hasil ditemukan."))
        return
    for e in entries:
        no_str = c(C.MAGENTA + C.BOLD, f"  [{e['no']:>2}]")
        title  = c(C.WHITE + C.BOLD, truncate(e['title'], W - 10))
        genres = "  ".join(genre_badge(g) for g in e['genres']) if e['genres'] else c(C.GRAY, "-")
        rel    = c(C.GRAY, f"🕐 {e['released']}")
        print(f"{no_str} {title}")
        print(f"       {genres}")
        print(f"       {rel}")
        print(c(C.GRAY, "  " + "·"*(W - 3)))
    print()

def print_detail(d):
    print()
    header_bar(f"📺  DETAIL ANIME", C.BG_BLUE, C.WHITE)
    print()
    print(c(C.WHITE + C.BOLD, f"  {d['title']}"))
    if d['japanese'] != "-":
        print(c(C.GRAY, f"  {d['japanese']}"))
    print()

    genres_str = "  ".join(genre_badge(g) for g in d['genres']) if d['genres'] else c(C.GRAY, "-")
    sc = d['score']
    score_str  = c(score_color(sc), f"★ {sc}") if sc != "-" else c(C.GRAY, "-")
    stat_str   = status_badge(d['status'])

    print(f"  {c(C.GRAY,'Genre      ')}  {genres_str}")
    print(f"  {c(C.GRAY,'Season     ')}  {c(C.CYAN, d['season'])}")
    print(f"  {c(C.GRAY,'Producers  ')}  {c(C.WHITE, d['producers'])}")
    print(f"  {c(C.GRAY,'Type       ')}  {c(C.YELLOW, d['type'])}")
    print(f"  {c(C.GRAY,'Status     ')}  {stat_str}")
    print(f"  {c(C.GRAY,'Episodes   ')}  {c(C.WHITE, d['total_eps'])}")
    print(f"  {c(C.GRAY,'Score      ')}  {score_str}")
    print(f"  {c(C.GRAY,'Duration   ')}  {c(C.WHITE, d['duration'])}")
    print(f"  {c(C.GRAY,'Released   ')}  {c(C.WHITE, d['released_on'])}")
    print()
    bar("─", C.GRAY)

    print(c(C.CYAN + C.BOLD, "  📝  SINOPSIS"))
    bar("─", C.GRAY)
    syn = d["synopsis"]
    words = syn.split()
    line, col = "  ", 2
    for w in words:
        if col + len(w) + 1 > W - 2:
            print(c(C.WHITE, line))
            line, col = "  " + w + " ", 2 + len(w) + 1
        else:
            line += w + " "
            col  += len(w) + 1
    if line.strip():
        print(c(C.WHITE, line))
    print()
    bar("─", C.GRAY)

def print_download_menu(download):
    if not download:
        print(c(C.RED, "  ✗  Tidak ada link download."))
        return

    keys = list(download.keys())
    print()
    header_bar("📥  PILIH RESOLUSI", C.BG_BLACK, C.CYAN)
    print()

    res_icons = {"360P": "📱", "480P": "📺", "720P": "🖥 ", "1080P": "🎬", "1080p": "🎬"}
    for i, k in enumerate(keys, 1):
        icon = res_icons.get(k, "📦")
        cnt  = len(download[k])
        print(f"  {c(C.CYAN+C.BOLD, f'[{i}]')} {icon} {c(C.WHITE+C.BOLD, k)}"
              f"  {c(C.GRAY, f'({cnt} mirror)')}")
    print(f"  {c(C.GRAY, '[0]')} {c(C.GRAY, '↩  Kembali')}")
    print()
    bar("─", C.GRAY)

    try:
        ch = int(input(f"  {c(C.CYAN,'Pilih nomor')} : ").strip())
    except ValueError:
        return
    if ch == 0 or ch > len(keys):
        return

    res_key = keys[ch - 1]
    mirrors = download[res_key]
    print()
    header_bar(f"🔗  {res_key} — {len(mirrors)} Mirror", C.BG_BLACK, C.GREEN)
    print()

    mirror_icons = {
        "google": "🟢", "mega": "🔴", "drive": "🟡", "acefile": "📁",
        "terabox": "☁ ", "hxfile": "📂", "pixeldrain": "💧", "akirabox": "📦",
        "megaup": "⬆ ", "uptobox": "📤", "buzzheavier": "⚡", "mirror": "🪞",
    }

    for i, lk in enumerate(mirrors, 1):
        raw, dec = lk["url_raw"], lk["url"]
        name     = lk["mirror"]
        icon     = "🔗"
        for k, v in mirror_icons.items():
            if k in name.lower() or k in raw.lower():
                icon = v; break

        print(f"  {c(C.GRAY, f'[{i}]')} {icon}  {c(C.WHITE+C.BOLD, name)}")
        if raw != dec:
            print(f"       {c(C.GREEN, '✅ Decoded :')} {c(C.GREEN, dec)}")
            print(f"       {c(C.GRAY,  '🔒 Raw     :')} {c(C.GRAY,  raw)}")
        else:
            print(f"       {c(C.CYAN, dec)}")
        print()
    bar("─", C.GRAY)

def prompt(text):
    return input(f"\n  {c(C.YELLOW + C.BOLD, '▶')} {c(C.WHITE, text)} : ").strip()

def goto_detail(url):
    print(c(C.GRAY, f"\n  ⏳ Mengambil detail ..."))
    d = scrape_detail(url)
    if not d:
        print(c(C.RED, "  ✗  Gagal mengambil detail."))
        return
    print_detail(d)
    while True:
        print(f"  {c(C.CYAN,'[D]')} {c(C.WHITE,'Link Download')}   "
              f"{c(C.GRAY,'[K]')} {c(C.GRAY,'Kembali')}")
        bar("─", C.GRAY)
        act = input(f"  {c(C.YELLOW+C.BOLD,'▶')} {c(C.WHITE,'Pilih')} : ").strip().upper()
        if act == "D":
            print_download_menu(d["download"])
        elif act == "K":
            break

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print()
    banner = [
        "██╗  ██╗██╗   ██╗███████╗ ██████╗ ███╗   ██╗██╗███╗   ███╗███████╗",
        "██║ ██╔╝██║   ██║██╔════╝██╔═══██╗████╗  ██║██║████╗ ████║██╔════╝",
        "█████╔╝ ██║   ██║███████╗██║   ██║██╔██╗ ██║██║██╔████╔██║█████╗  ",
        "██╔═██╗ ██║   ██║╚════██║██║   ██║██║╚██╗██║██║██║╚██╔╝██║██╔══╝  ",
        "██║  ██╗╚██████╔╝███████║╚██████╔╝██║ ╚████║██║██║ ╚═╝ ██║███████╗",
        "╚═╝  ╚═╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝     ╚═╝╚══════╝",
    ]
    for line in banner:
        pad = max(0, (W - len(line)) // 2)
        print(c(C.CYAN + C.BOLD, " " * pad + line))

    print(c(C.GRAY, " " * max(0,(W-40)//2) + "─"*40))
    sub = "Anime Subtitle Indonesia — Scraper CLI"
    print(c(C.YELLOW, " " * max(0,(W-len(sub))//2) + sub))
    print()

    print(c(C.GRAY, f"  ⏳ Mengambil upload terbaru ..."))
    latest = scrape_latest(1)
    if latest:
        print_latest(latest)
    else:
        print(c(C.RED, "  ✗  Gagal memuat beranda."))

    while True:
        print()
        header_bar("MENU UTAMA", C.BG_BLACK, C.YELLOW)
        print()
        print(f"  {c(C.CYAN+C.BOLD,'[1]')}  🆕  Refresh upload terbaru")
        print(f"  {c(C.CYAN+C.BOLD,'[2]')}  🔍  Search anime")
        print(f"  {c(C.CYAN+C.BOLD,'[3]')}  🔗  Buka detail via URL")
        print(f"  {c(C.GRAY,  '[0]')}  👋  Keluar")
        print()
        bar("─", C.GRAY)
        choice = input(f"  {c(C.YELLOW+C.BOLD,'▶')} {c(C.WHITE,'Pilih')} : ").strip()

        if choice == "1":
            print(c(C.GRAY, "\n  ⏳ Memuat ulang ..."))
            latest = scrape_latest(1)
            if latest:
                print_latest(latest)
                pick = prompt("Pilih nomor untuk detail (Enter=skip)")
                if pick.isdigit() and 1 <= int(pick) <= len(latest):
                    goto_detail(latest[int(pick)-1]["url"])
            else:
                print(c(C.RED, "  ✗  Gagal."))

        elif choice == "2":
            query = prompt("Kata kunci")
            if not query: continue
            print(c(C.GRAY, f"\n  ⏳ Mencari '{query}' ..."))
            results = search_anime(query)
            print_search(results, query)
            if results:
                pick = prompt("Pilih nomor untuk detail (Enter=skip)")
                if pick.isdigit() and 1 <= int(pick) <= len(results):
                    goto_detail(results[int(pick)-1]["url"])

        elif choice == "3":
            url_in = prompt("Masukkan URL kusonime")
            if url_in:
                goto_detail(url_in)

        elif choice == "0":
            print()
            print(c(C.CYAN + C.BOLD, "  Sampai jumpa! 👋"))
            print()
            break

if __name__ == "__main__":
    main()
