import os
import io
import re
import glob
import json
import base64
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

CARPETA_DATOS = "."
EXTS = ("*.jpg", "*.jpeg", "*.png", "*.bmp")

st.set_page_config(page_title="Visor Cine TAC", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("🔐 Inicie sesión primero en la página principal.")
    st.stop()


def natural(t):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", t)]


@st.cache_data(show_spinner="Cargando cortes...")
def cargar(items, max_lado):
    out = []
    for ruta, _mtime in items:
        im = Image.open(ruta).convert("RGB")
        im.thumbnail((max_lado, max_lado))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        out.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
    return out


st.title("🎞️ Visor Cine TAC / RM")

estudios = sorted(
    d for d in os.listdir(CARPETA_DATOS)
    if d.startswith("estudio_") and os.path.isdir(os.path.join(CARPETA_DATOS, d))
)
if not estudios:
    st.info("Aún no hay estudios guardados.")
    st.stop()

c1, c2, c3 = st.columns(3)
with c1:
    estudio = st.selectbox("Paciente (estudio):", estudios)
base = os.path.join(CARPETA_DATOS, estudio)

secuencias = {}
for sub in sorted(os.listdir(base)):
    p = os.path.join(base, sub)
    if os.path.isdir(p):
        fs = []
        for e in EXTS:
            fs.extend(glob.glob(os.path.join(p, e)))
        if fs:
            secuencias[sub] = sorted(fs, key=natural)
if not secuencias:
    fs = []
    for e in EXTS:
        fs.extend(glob.glob(os.path.join(base, e)))
    if fs:
        secuencias["Estudio general"] = sorted(fs, key=natural)
if not secuencias:
    st.warning("Este estudio no tiene imágenes.")
    st.stop()

with c2:
    nombre_sec = st.selectbox("Secuencia:", list(secuencias.keys()))
with c3:
    max_lado = st.select_slider("Calidad / tamaño máx. (px):", [512, 768, 1024, 1280], value=768)

archivos = secuencias[nombre_sec]
items = tuple((f, os.path.getmtime(f)) for f in archivos)
imgs = cargar(items, max_lado)

HTML = """
<style>
  body{margin:0;font-family:sans-serif;color:#fff;background:transparent}
  #box{display:flex;flex-direction:column;align-items:center;gap:10px}
  #im{max-width:100%;max-height:__H__px;background:#000;border-radius:6px;user-select:none}
  .row{display:flex;align-items:center;gap:10px;width:100%;max-width:900px}
  #sl{flex:1;accent-color:#ff4b4b;cursor:pointer}
  button{border:1px solid #888;border-radius:6px;padding:6px 14px;background:#222;color:#fff;cursor:pointer;font-size:14px}
  button:hover{border-color:#ff4b4b}
  #ct{min-width:80px;text-align:right;font-weight:bold}
  label{font-size:12px}
</style>
<div id="box">
  <img id="im">
  <div class="row">
    <input id="sl" type="range" min="0" max="0" value="0">
    <span id="ct">1 / 1</span>
  </div>
  <div class="row">
    <button id="pl">▶ Reproducir</button>
    <label>Velocidad <input id="fps" type="range" min="1" max="30" value="12"></label>
    <span style="font-size:11px;color:#aaa;margin-left:auto">Arrastra la barra o usa la rueda del mouse / flechas</span>
  </div>
</div>
<script>
const imgs = __DATA__;
const im=document.getElementById('im'), sl=document.getElementById('sl'),
      ct=document.getElementById('ct'), pl=document.getElementById('pl'),
      fps=document.getElementById('fps');
let i=0, timer=null;
sl.max = imgs.length-1;
function show(n){
  i=Math.max(0,Math.min(imgs.length-1,n));
  im.src=imgs[i]; sl.value=i; ct.textContent=(i+1)+' / '+imgs.length;
}
function stop(){ if(timer){clearInterval(timer);timer=null;} pl.textContent='▶ Reproducir'; }
function start(){
  stop(); pl.textContent='❚❚ Pausar';
  timer=setInterval(()=>show(i>=imgs.length-1?0:i+1), 1000/fps.value);
}
pl.onclick=()=> timer?stop():start();
fps.oninput=()=>{ if(timer) start(); };
sl.oninput=()=>show(+sl.value);
document.getElementById('box').addEventListener('wheel',e=>{
  e.preventDefault(); show(i+(e.deltaY>0?1:-1));
},{passive:false});
document.addEventListener('keydown',e=>{
  if(e.key==='ArrowRight'||e.key==='ArrowDown') show(i+1);
  if(e.key==='ArrowLeft'||e.key==='ArrowUp') show(i-1);
  if(e.key===' '){e.preventDefault(); timer?stop():start();}
});
show(0);
</script>
"""

alto = 650
html = HTML.replace("__DATA__", json.dumps(imgs)).replace("__H__", str(alto))
st.caption(f"{len(imgs)} cortes en «{nombre_sec}»")
components.html(html, height=alto + 130, scrolling=False)
