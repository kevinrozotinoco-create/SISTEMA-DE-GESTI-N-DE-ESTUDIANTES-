import os
import re
import io
import glob
import zipfile
import streamlit as st

CARPETA_DATOS = "."
EXTS = (".jpg", ".jpeg", ".png", ".bmp")

st.set_page_config(page_title="Agregar secuencia TAC", layout="wide")

if not st.session_state.get("autenticado"):
    st.warning("🔐 Inicie sesión primero en la página principal.")
    st.stop()


def orden_natural(texto):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", texto)]


st.title("🎞️ Agregar secuencia de imágenes (TAC / RM)")

estudios = sorted(
    d.replace("estudio_", "", 1)
    for d in os.listdir(CARPETA_DATOS)
    if d.startswith("estudio_") and os.path.isdir(os.path.join(CARPETA_DATOS, d))
)

col1, col2 = st.columns(2)
with col1:
    existente = st.selectbox("Paciente con estudio existente:", ["-- Escribir otra cédula --"] + estudios)
    otra = st.text_input("O escriba la cédula del paciente:").strip().replace(" ", "")
    id_paciente = otra if otra else ("" if existente.startswith("--") else existente)
with col2:
    nombre_sec = st.text_input("Nombre de la secuencia:", value="Secuencia TAC").strip()

zip_file = st.file_uploader("📦 Carpeta en ZIP", type=["zip"])
sueltas = st.file_uploader(
    "…o seleccione varias imágenes (JPG / PNG / BMP)",
    type=["jpg", "jpeg", "png", "bmp"],
    accept_multiple_files=True,
)

if st.button("💾 Guardar secuencia", type="primary"):
    if not id_paciente or not nombre_sec:
        st.error("Indique la cédula del paciente y el nombre de la secuencia.")
    elif not zip_file and not sueltas:
        st.error("Suba un ZIP o al menos una imagen.")
    else:
        items = []
        if zip_file:
            with zipfile.ZipFile(io.BytesIO(zip_file.getbuffer())) as zf:
                for info in zf.infolist():
                    base = os.path.basename(info.filename)
                    if (info.is_dir() or "__MACOSX" in info.filename
                            or base.startswith(".")
                            or not base.lower().endswith(EXTS)):
                        continue
                    items.append((info.filename, zf.read(info)))
        for f in sueltas or []:
            items.append((f.name, f.getvalue()))

        if not items:
            st.error("No se encontraron imágenes válidas.")
        else:
            items.sort(key=lambda x: orden_natural(x[0]))
            destino = os.path.join(CARPETA_DATOS, f"estudio_{id_paciente}", nombre_sec)
            os.makedirs(destino, exist_ok=True)
            for viejo in glob.glob(os.path.join(destino, "corte_*")):
                os.remove(viejo)
            for i, (nombre, datos) in enumerate(items, start=1):
                ext = os.path.splitext(nombre)[1].lower()
                with open(os.path.join(destino, f"corte_{i:03d}{ext}"), "wb") as out:
                    out.write(datos)
            st.success(f"✅ {len(items)} cortes guardados en «{nombre_sec}» del paciente {id_paciente}.")
            st.cache_data.clear()
            