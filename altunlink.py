"""AltunLink - Telefon ile bilgisayar arasında aynı Wi-Fi üzerinden dosya köprüsü."""
import os, sys, json, socket, secrets, threading, queue, webbrowser, itertools
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote, quote

APP = "AltunLink"
SAVE_DIR = os.path.join(os.path.expanduser("~"), "Downloads", APP)
events = queue.Queue()          # sunucu -> arayüz
shared = []                     # bilgisayardan telefona gönderilecek dosyalar
TOKEN = secrets.token_urlsafe(8)
ids = itertools.count(1)

PAGE = """<!DOCTYPE html><html lang=tr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>AltunLink</title><style>
body{margin:0;background:#050b1f;color:#eaf2ff;font-family:system-ui,sans-serif;padding:18px}
h1{font-size:22px;margin:0 0 4px}p{color:#8aa4d6;font-size:14px}
.b{display:block;width:100%;padding:14px;border:0;border-radius:12px;background:linear-gradient(#22b8ff,#0a6cff);color:#00112e;font-weight:700;font-size:16px;margin:14px 0;text-align:center}
.c{background:#0a1534;border:1px solid #1a3a8a;border-radius:12px;padding:12px;margin:8px 0;font-size:14px;word-break:break-all}
.p{height:7px;background:#10245e;border-radius:5px;margin-top:8px;overflow:hidden}.p div{height:100%;width:0;background:linear-gradient(90deg,#0a6cff,#2de0ff)}
a{color:#2de0ff}</style></head><body><h1>AltunLink</h1><p>Bilgisayarla bağlantı kuruldu.</p>
<label class=b>Bilgisayara dosya gönder<input id=f type=file multiple hidden></label><div id=u></div>
<h1 style="font-size:17px;margin-top:22px">Bilgisayardan gelenler</h1><div id=l><p>Henüz dosya yok.</p></div>
<script>
const T=new URLSearchParams(location.search).get('t');
f.onchange=()=>[...f.files].forEach(send);
function send(file){const d=document.createElement('div');d.className='c';
d.innerHTML='<span>'+file.name.replace(/[<>&]/g,'')+'</span><div class=p><div></div></div><small></small>';u.prepend(d);
const x=new XMLHttpRequest();x.open('POST','/up?t='+T+'&name='+encodeURIComponent(file.name));
x.upload.onprogress=e=>{const p=Math.round(e.loaded/e.total*100);d.querySelector('.p div').style.width=p+'%';d.querySelector('small').textContent='%'+p};
x.onload=()=>d.querySelector('small').textContent=x.status==200?'Gönderildi':'Hata';
x.onerror=()=>d.querySelector('small').textContent='Bağlantı koptu';x.send(file)}
async function poll(){try{const r=await (await fetch('/list?t='+T)).json();
if(r.length)l.innerHTML=r.map((n,i)=>'<div class=c><a href="/dl/'+i+'?t='+T+'">'+n.replace(/[<>&]/g,'')+'</a></div>').join('')}catch(e){}}
poll();setInterval(poll,3000);
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _ok(self):
        q = parse_qs(urlparse(self.path).query)
        if q.get("t", [""])[0] != TOKEN:
            self.send_error(403, "Invalid pairing code"); return None
        return q
    def _send(self, body, ctype="text/html; charset=utf-8"):
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        q = self._ok()
        if q is None: return
        path = urlparse(self.path).path
        if path == "/": return self._send(PAGE.encode())
        if path == "/list":
            return self._send(json.dumps([os.path.basename(p) for p in shared]).encode(), "application/json")
        if path.startswith("/dl/"):
            try: p = shared[int(path[4:])]
            except (ValueError, IndexError): return self.send_error(404)
            size, fid, name = os.path.getsize(p), next(ids), os.path.basename(p)
            self.send_response(200); self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(name))
            self.end_headers(); events.put(("start", fid, name, size, "↓")); sent = 0
            try:
                with open(p, "rb") as f:
                    while chunk := f.read(1 << 20):
                        self.wfile.write(chunk); sent += len(chunk); events.put(("prog", fid, sent))
                events.put(("done", fid))
            except OSError: events.put(("fail", fid))
            return
        self.send_error(404)
    def do_POST(self):
        q = self._ok()
        if q is None or urlparse(self.path).path != "/up": return
        name = os.path.basename(unquote(q.get("name", ["dosya"])[0])) or "dosya"
        size, fid = int(self.headers.get("Content-Length", 0)), next(ids)
        os.makedirs(SAVE_DIR, exist_ok=True)
        base, ext = os.path.splitext(name); dest, n = os.path.join(SAVE_DIR, name), 1
        while os.path.exists(dest): dest = os.path.join(SAVE_DIR, f"{base} ({n}){ext}"); n += 1
        events.put(("start", fid, name, size, "↑")); got = 0
        try:
            with open(dest, "wb") as f:
                while got < size:
                    chunk = self.rfile.read(min(1 << 20, size - got))
                    if not chunk: raise OSError("koptu")
                    f.write(chunk); got += len(chunk); events.put(("prog", fid, got))
            events.put(("done", fid)); self._send(b"ok", "text/plain")
        except OSError:
            events.put(("fail", fid))
            try: os.remove(dest)
            except OSError: pass

def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(("10.255.255.255", 1)); return s.getsockname()[0]
    except OSError: return "127.0.0.1"
    finally: s.close()

def start_server():
    for port in range(8765, 8790):
        try: srv = ThreadingHTTPServer(("0.0.0.0", port), Handler); break
        except OSError: continue
    else: raise RuntimeError("Boş port bulunamadı")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]

def res(p):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), p)

def fmt(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024 or u == "GB": return f"{b:.0f} {u}" if u == "B" else f"{b:.1f} {u}"
        b /= 1024

def main():
    import tkinter as tk
    from tkinter import ttk, filedialog
    import qrcode
    from PIL import ImageTk
    BG, PANEL, NEON, TX, MUT = "#050b1f", "#0a1534", "#22b8ff", "#eaf2ff", "#8aa4d6"
    port = start_server(); url = f"http://{lan_ip()}:{port}/?t={TOKEN}"
    root = tk.Tk(); root.title(APP); root.geometry("1000x640"); root.minsize(860, 560); root.configure(bg=BG)
    try: root.iconphoto(True, tk.PhotoImage(file=res("assets/icon.png")))
    except tk.TclError: pass
    st = ttk.Style(root); st.theme_use("clam")
    st.configure("TProgressbar", troughcolor="#10245e", background=NEON, bordercolor=BG, lightcolor=NEON, darkcolor=NEON)
    def lab(p, t, size=11, fg=TX, bold=False, **k):
        return tk.Label(p, text=t, bg=k.pop("bg", PANEL), fg=fg, font=("Segoe UI", size, "bold" if bold else "normal"), **k)
    def btn(p, t, cmd):
        return tk.Button(p, text=t, command=cmd, bg=NEON, fg="#00112e", activebackground="#2de0ff", relief="flat",
                         font=("Segoe UI", 11, "bold"), padx=14, pady=8, cursor="hand2")
    left = tk.Frame(root, bg=PANEL, highlightbackground="#1a3a8a", highlightthickness=1); left.pack(side="left", fill="y", padx=(18, 9), pady=18)
    lab(left, "Telefonu eşleştir", 15, bold=True).pack(padx=20, pady=(18, 4))
    lab(left, "Aynı Wi-Fi'a bağlan, telefonun\nkamerasıyla kodu okut.", 10, MUT).pack()
    img = qrcode.make(url).convert("RGB").resize((260, 260)); photo = ImageTk.PhotoImage(img)
    tk.Label(left, image=photo, bg="white").pack(pady=14, padx=20)
    lab(left, url.split("?")[0], 10, MUT).pack(); btn(left, "Telefona dosya gönder", lambda: send_files()).pack(pady=(16, 6), padx=20, fill="x")
    btn(left, "Gelen dosyalar klasörü", lambda: (os.makedirs(SAVE_DIR, exist_ok=True), os.startfile(SAVE_DIR) if os.name == "nt" else webbrowser.open(SAVE_DIR))).pack(padx=20, fill="x")
    lab(left, "Bizi takip et", 10, MUT).pack(pady=(18, 4))
    soc = tk.Frame(left, bg=PANEL); soc.pack(padx=20, pady=(0, 18), fill="x")
    for name, link, c in (("YouTube", "https://www.youtube.com/@Altun67", "#ff3b3b"), ("Instagram", "https://www.instagram.com/altunn_67/", "#ff3d8b"), ("TikTok", "https://www.tiktok.com/@altunn_67", "#2de0ff")):
        tk.Button(soc, text="● " + name, command=lambda l=link: webbrowser.open(l), bg="#14161f", fg=c, activebackground="#1d2030", relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2", pady=5).pack(fill="x", pady=2)
    right = tk.Frame(root, bg=PANEL, highlightbackground="#1a3a8a", highlightthickness=1); right.pack(side="left", fill="both", expand=True, padx=(9, 18), pady=18)
    lab(right, "Aktarımlar", 15, bold=True).pack(anchor="w", padx=20, pady=(18, 4))
    empty = lab(right, "Henüz aktarım yok. Telefonla QR kodu okut ve bir dosya gönder.", 11, MUT); empty.pack(padx=20, pady=20)
    rows = {}
    def send_files():
        for p in filedialog.askopenfilenames(title="Telefona gönderilecek dosyalar"):
            if p not in shared: shared.append(p)
    def tick():
        try:
            while True:
                ev = events.get_nowait(); k, fid = ev[0], ev[1]
                if k == "start":
                    empty.pack_forget(); fr = tk.Frame(right, bg=PANEL); fr.pack(fill="x", padx=20, pady=6, side="top")
                    top = tk.Frame(fr, bg=PANEL); top.pack(fill="x")
                    lab(top, f"{ev[4]}  {ev[2]}", 11).pack(side="left"); info = lab(top, "0%", 10, NEON); info.pack(side="right")
                    bar = ttk.Progressbar(fr, maximum=max(ev[3], 1)); bar.pack(fill="x", pady=(4, 0)); rows[fid] = (bar, info, ev[3])
                elif fid in rows:
                    bar, info, total = rows[fid]
                    if k == "prog": bar["value"] = ev[2]; info.config(text=f"{fmt(ev[2])} / {fmt(total)}  ·  %{ev[2] * 100 // max(total, 1)}")
                    elif k == "done": bar["value"] = total; info.config(text="Bitti ✓", fg="#3df0a8")
                    elif k == "fail": info.config(text="Hata ✗", fg="#ff5a5a")
        except queue.Empty: pass
        root.after(100, tick)
    tick(); root.mainloop()

if __name__ == "__main__": main()
