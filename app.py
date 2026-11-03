import os
import glob
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageEnhance, ImageOps
import base64

# 1. Configuración de la página web Streamlit
st.set_page_config(
    page_title="Visualizador DSA", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

CARPETA_DATOS = "."

# Componente adicional del visor: control por arrastre, rueda del ratón y reproducción.
parent_dir = os.path.abspath(os.path.dirname(__file__))
component_dir = os.path.join(parent_dir, "cine_scroll_component")

cine_scroll = components.declare_component(
    "cine_scroll",
    path=component_dir
)

# ==============================================================================
# 🔐 MÓDULO DE AUTENTICACIÓN Y SEGURIDAD
# ==============================================================================
USUARIOS_VALIDOS = {
    "darhienn": "1995",
    "Darhienn": "1995",
    "darien": "1995",
    "Darien": "1995",
    "admin": "pacs2026",
    "medico": "radiologia123",
    "kevin": "compensar2026"
}

def inicializar_sesion():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = None

inicializar_sesion()

if not st.session_state.autenticado:
    def obtener_base64_imagen(ruta_imagen):
        with open(ruta_imagen, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()

    try:
        img_base64 = obtener_base64_imagen("fondo.jpg")
        background_style = f'background-image: url("data:image/jpeg;base64,{img_base64}");'
    except Exception:
        background_style = 'background-color: #0e1117;'

    st.markdown(
        f"""
        <style>
        .stApp {{
            {background_style}
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .block-container {{
            padding-top: 55vh !important;
        }}
        div[data-testid="stForm"] {{
            background-color: rgba(5, 10, 25, 0.75);
            padding: 2rem;
            border-radius: 15px;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(0, 150, 255, 0.3);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        }}
        label {{
            color: #ffffff !important;
            font-weight: 500;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("form_login"):
            st.subheader("🔐 Iniciar Sesión")
            usr = st.text_input("Usuario:").strip()
            pwd = st.text_input("Contraseña:", type="password").strip()
            btn_login = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
            
            if btn_login:
                if usr in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usr] == pwd:
                    st.session_state.autenticado = True
                    st.session_state.usuario = usr
                    st.success("✅ Acceso concedido. Cargando sistema...")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()

# ==============================================================================
# 📂 LECTURA DE DATOS CLÍNICOS Y ARCHIVOS DE PACIENTES
# ==============================================================================
@st.cache_data(ttl=1)
def cargar_todos_los_pacientes(carpeta):
    pacientes = {}
    archivos_excel = glob.glob(os.path.join(carpeta, "*.xlsx"))
    
    for archivo in archivos_excel:
        try:
            df = pd.read_excel(archivo, header=None)
            info = {}
            
            for _, row in df.iterrows():
                key = str(row[0]).strip() if pd.notna(row[0]) else ""
                val = row[1] if len(row) > 1 and pd.notna(row[1]) else ""
                
                if isinstance(val, (int, float)) and not pd.isna(val):
                    val = str(int(val))
                else:
                    val = str(val).strip()
                    
                if key and key.lower() != "nan":
                    info[key] = val

            id_paciente = None
            for idx, row in df.iterrows():
                campo = str(row[0]).strip() if pd.notna(row[0]) else ""
                if campo.lower() == "id paciente":
                    if len(row) > 1 and pd.notna(row[1]):
                        val = row[1]
                        val_str = str(int(val)) if isinstance(val, (int, float)) else str(val).strip()
                        if val_str and val_str.lower() != "nan":
                            id_paciente = val_str
                            break

            if id_paciente:
                id_paciente = id_paciente.replace(" ", "").replace(".0", "")

                p_nombre = info.get('PRIMER NOMBRE', info.get('PRIEMER NOMBRE', ''))
                s_nombre = info.get('SEGUNDO NOMBRE', '')
                p_apellido = info.get('PRIMER APELLIDO', '')
                s_apellido = info.get('SEGUNDO APELLIDO', '')
                
                nombre_completo = f"{p_nombre} {s_nombre} {p_apellido} {s_apellido}".strip()
                nombre_completo = " ".join(nombre_completo.split())

                pacientes[id_paciente] = {
                    "archivo": archivo,
                    "id": id_paciente,
                    "datos": info,
                    "nombre": nombre_completo,
                    "edad": info.get("Edad", "N/A"),
                    "sexo": info.get("sexo", "N/A"),
                    "motivo": info.get("Motivo de consulta", "N/A"),
                    "diagnostico": info.get("Diagnóstico presuntivo", "N/A"),
                    "estudio": info.get("Tipo de estudio", "N/A"),
                    "modalidad": info.get("Modalidad diagnóstica", "N/A"),
                    "estado": info.get("Estado del estudio", "N/A"),
                    "ruta_imagen": info.get("Ruta Soporte", "")
                }
        except Exception as e:
            st.error(f"Error procesando {archivo}: {e}")
            
    return pacientes

# ==============================================================================
# 🖥️ INTERFAZ PRINCIPAL Y BARRA LATERAL
# ==============================================================================
with st.sidebar:
    st.write(f"👤 **Usuario activo:** `{st.session_state.usuario.upper()}`")
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.usuario = None
        st.rerun()
    st.divider()

st.title("Visualizador DSA")

tab_buscar, tab_nuevo = st.tabs(["🔍 Consultar Paciente y Visor PACS", "➕ Registrar Nuevo Paciente"])

pacientes = cargar_todos_los_pacientes(CARPETA_DATOS)

# ==============================================================================
# --- PESTAÑA 1: VISOR PACS MULTISECUENCIA Y CONSULTA CLÍNICA ---
# ==============================================================================
with tab_buscar:
    st.sidebar.header("📋 Historias Registradas")
    
    opcion_lista = "-- Seleccionar de la lista --"
    if pacientes:
        opciones = {f"{p['id']} - {p['nombre']}": p['id'] for p in pacientes.values()}
        seleccion_combo = st.sidebar.selectbox("Seleccione un paciente:", [opcion_lista] + list(opciones.keys()))
    else:
        st.sidebar.warning("No se encontraron archivos de pacientes.")
        seleccion_combo = opcion_lista

    cedula_escrita = st.text_input("🔍 Ingrese o busque la Cédula del Paciente:").strip().replace(" ", "")

    cedula_final = ""
    if cedula_escrita:
        cedula_final = cedula_escrita
    elif seleccion_combo != opcion_lista:
        cedula_final = opciones[seleccion_combo]

    if cedula_final:
        if cedula_final in pacientes:
            p = pacientes[cedula_final]
            st.success(f"**Paciente:** {p['nombre']} | **Cédula:** {cedula_final} | **Modalidad:** {p['modalidad']} | **Estudio:** {p['estudio']}")
            
            col_info, col_visor = st.columns([1, 2])
            
            with col_info:
                st.subheader("📋 Datos del Registro RIS")
                st.write(f"**Edad / Sexo:** {p['edad']} | {p['sexo']}")
                st.write(f"**Tipo de Estudio:** {p['estudio']}")
                st.write(f"**Estado del Estudio:** {p['estado']}")
                st.write(f"**Motivo Consulta:** {p['motivo']}")
                st.write(f"**Diagnóstico Presuntivo:** {p['diagnostico']}")
                
                st.divider()
                st.subheader("⚙️ Herramientas PACS")
                brillo = st.slider("Brillo", 0.2, 3.0, 1.0, 0.1)
                contraste = st.slider("Contraste", 0.2, 3.0, 1.0, 0.1)
                invertir = st.checkbox("Invertir Colores (Negativo Radiológico)")
                rotacion = st.selectbox("Rotación (°)", [0, 90, 180, 270])
                ancho = st.slider("Escala / Zoom (px)", 300, 1000, 600, 50)
                
                st.divider()
                if st.button("🗑️ Eliminar este Paciente del Sistema", type="primary"):
                    if os.path.exists(p['archivo']):
                        os.remove(p['archivo'])
                    ruta_img_del = os.path.join(CARPETA_DATOS, p['ruta_imagen'])
                    if os.path.exists(ruta_img_del) and os.path.isfile(ruta_img_del):
                        os.remove(ruta_img_del)
                        
                    st.success(f"Ficha de {p['nombre']} eliminada correctamente.")
                    st.cache_data.clear()
                    st.rerun()
                
            with col_visor:
                st.subheader("🖼️ Visor de Imágenes Clínicas PACS (Multi-Secuencia)")
                
                carpeta_estudio = os.path.join(CARPETA_DATOS, f"estudio_{p['id']}")
                secuencias_disponibles = {}
                
                if os.path.exists(carpeta_estudio) and os.path.isdir(carpeta_estudio):
                    elementos = os.listdir(carpeta_estudio)
                    for elem in elementos:
                        path_elem = os.path.join(carpeta_estudio, elem)
                        if os.path.isdir(path_elem):
                            imgs_sec = []
                            for ext in ["*.jpeg", "*.jpg", "*.png", "*.bmp"]:
                                imgs_sec.extend(glob.glob(os.path.join(path_elem, ext)))
                            if imgs_sec:
                                secuencias_disponibles[elem] = sorted(imgs_sec)
                    
                    if not secuencias_disponibles:
                        imgs_sueltas = []
                        for ext in ["*.jpeg", "*.jpg", "*.png", "*.bmp"]:
                            imgs_sueltas.extend(glob.glob(os.path.join(carpeta_estudio, ext)))
                        if imgs_sueltas:
                            secuencias_disponibles["Estudio General / Único"] = sorted(imgs_sueltas)

                if not secuencias_disponibles:
                    ruta_principal = os.path.join(CARPETA_DATOS, p["ruta_imagen"])
                    if os.path.exists(ruta_principal) and os.path.isfile(ruta_principal):
                        secuencias_disponibles["Soporte Principal"] = [ruta_principal]

                if secuencias_disponibles:
                    nombres_secuencias = list(secuencias_disponibles.keys())
                    secuencia_seleccionada = st.selectbox("📂 Seleccionar Secuencia / Ventana Radiológica:", nombres_secuencias)
                    
                    lista_imagenes = secuencias_disponibles[secuencia_seleccionada]
                    total_cortes = len(lista_imagenes)
                    
                    if total_cortes > 1:
                        st.info(f"🎞️ **Secuencia '{secuencia_seleccionada}':** {total_cortes} cortes en secuencia cargados.")
                        
                        # --- NAVEGACIÓN DE SECUENCIA: ARRASTRE, RUEDA Y REPRODUCCIÓN ---
                        idx_img = cine_scroll(
                            total=total_cortes,
                            initial_value=0,
                            key=f"cine_{p['id']}_{secuencia_seleccionada}",
                            default=0
                        )
                        idx_img = max(0, min(int(idx_img), total_cortes - 1))
                        
                        img_sel_path = lista_imagenes[idx_img]
                        st.caption(f"📍 Corte actual: **{idx_img + 1}** de {total_cortes}")
                    else:
                        img_sel_path = lista_imagenes[0]

                    img = Image.open(img_sel_path)
                    
                    if invertir:
                        if img.mode == 'RGBA':
                            r, g, b, a = img.split()
                            rgb_img = Image.merge('RGB', (r, g, b))
                            inv = ImageOps.invert(rgb_img)
                            r, g, b = inv.split()
                            img = Image.merge('RGBA', (r, g, b, a))
                        else:
                            img = ImageOps.invert(img.convert('RGB'))
                            
                    if rotacion != 0:
                        img = img.rotate(-rotacion, expand=True)
                        
                    img = ImageEnhance.Brightness(img).enhance(brillo)
                    img = ImageEnhance.Contrast(img).enhance(contraste)
                    
                    st.image(img, width=ancho, caption=f"Secuencia: [{secuencia_seleccionada}] — Archivo: {os.path.basename(img_sel_path)}")
                else:
                    st.warning(f"⚠️ Soporte no disponible o estudio pendiente para el paciente: {p['nombre']}")
                    
# ==============================================================================
# --- PESTAÑA 2: FORMULARIO DE REGISTRO MULTI-SECUENCIA Y TAC ---
# ==============================================================================
with tab_nuevo:
    st.header("📝 Formulario de Registro Clínico RIS y TAC Multi-Secuencia")
    st.write("Diligencie los datos y cargue las imágenes organizadas por secuencias o ventanas radiológicas.")

    with st.form("form_nuevo_paciente", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            id_paciente = st.text_input("Cédula / ID Paciente *").strip()
            p_nombre = st.text_input("Primer Nombre *").strip()
            s_nombre = st.text_input("Segundo Nombre").strip()
            p_apellido = st.text_input("Primer Apellido *").strip()
            s_apellido = st.text_input("Segundo Apellido").strip()
            edad = st.text_input("Edad (Ej: 35 años)").strip()
            sexo = st.selectbox("Sexo", ["M", "F", "Otro"])

        with col2:
            motivo = st.text_area("Motivo de Consulta")
            sintomas = st.text_area("Síntomas Principales")
            antecedentes = st.text_area("Antecedentes")
            diagnostico = st.text_input("Diagnóstico Presuntivo")
            indicacion = st.text_input("Indicación Clínica")
            modalidad = st.selectbox("Modalidad Diagnóstica", ["CT", "TAC", "RX", "RM", "US", "OTRO"])
            tipo_estudio = st.text_input("Tipo de Estudio (Ej: TAC de Cráneo Simple)", value="TAC de Cráneo")
            estado = st.selectbox("Estado del Estudio", ["Realizado", "Pendiente", "En proceso"])

        st.divider()
        st.subheader("🧠 Carga de Imágenes por Secuencias / Ventanas (Ej. TAC de Cráneo)")
        st.write("Puedes subir diferentes fases o ventanas del estudio médico por separado:")
        
        secuencia_1_nombre = st.text_input("Nombre de la Secuencia 1 (Ej: Ventana Parenquimatosa / Simple)", value="Ventana ParenquIMatosa")
        archivos_sec_1 = st.file_uploader("Cortes de la Secuencia 1 (JPG / PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="sec1")
        
        st.markdown("---")
        secuencia_2_nombre = st.text_input("Nombre de la Secuencia 2 (Opcional - Ej: Ventana Ósea / Contrastada)", value="Ventana Ósea")
        archivos_sec_2 = st.file_uploader("Cortes de la Secuencia 2 (Opcional)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="sec2")

        boton_guardar = st.form_submit_button("💾 Guardar Estudio Multi-Secuencia en el Sistema")

    if boton_guardar:
        if not id_paciente or not p_nombre or not p_apellido:
            st.error("⚠️ Complete los campos obligatorios (Cédula, Primer Nombre y Primer Apellido).")
        else:
            nombre_imagen_soporte = "No disponible: el estudio está pendiente"
            dir_estudio = os.path.join(CARPETA_DATOS, f"estudio_{id_paciente}")
            os.makedirs(dir_estudio, exist_ok=True)
            
            primer_archivo_global = None

            if archivos_sec_1 and secuencia_1_nombre:
                dir_sec1 = os.path.join(dir_estudio, secuencia_1_nombre.strip())
                os.makedirs(dir_sec1, exist_ok=True)
                for idx, img_file in enumerate(archivos_sec_1):
                    ext = os.path.splitext(img_file.name)[1]
                    filename = f"corte_{idx+1}{ext}"
                    path_dest = os.path.join(dir_sec1, filename)
                    with open(path_dest, "wb") as f:
                        f.write(img_file.getbuffer())
                    if not primer_archivo_global:
                        primer_archivo_global = os.path.join(secuencia_1_nombre.strip(), filename)

            if archivos_sec_2 and secuencia_2_nombre:
                dir_sec2 = os.path.join(dir_estudio, secuencia_2_nombre.strip())
                os.makedirs(dir_sec2, exist_ok=True)
                for idx, img_file in enumerate(archivos_sec_2):
                    ext = os.path.splitext(img_file.name)[1]
                    filename = f"corte_{idx+1}{ext}"
                    path_dest = os.path.join(dir_sec2, filename)
                    with open(path_dest, "wb") as f:
                        f.write(img_file.getbuffer())
                    if not primer_archivo_global:
                        primer_archivo_global = os.path.join(secuencia_2_nombre.strip(), filename)

            if primer_archivo_global:
                nombre_imagen_soporte = primer_archivo_global
                src_first = os.path.join(dir_estudio, primer_archivo_global)
                if os.path.exists(src_first):
                    img_data_bytes = open(src_first, "rb").read()
                    with open(os.path.join(CARPETA_DATOS, f"{p_apellido}_{id_paciente}_principal.jpg"), "wb") as f:
                        f.write(img_data_bytes)
                    nombre_imagen_soporte = f"{p_apellido}_{id_paciente}_principal.jpg"

            datos_excel = [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", str(id_paciente)],
                ["ID Paciente", str(id_paciente)],
                ["PRIMER NOMBRE", p_nombre],
                ["SEGUNDO NOMBRE", s_nombre],
                ["PRIMER APELLIDO", p_apellido],
                ["SEGUNDO APELLIDO", s_apellido],
                ["Edad", edad],
                ["sexo", sexo],
                ["Motivo de consulta", motivo],
                ["Síntomas principales", sintomas],
                ["Antecedentes", antecedentes],
                ["Diagnóstico presuntivo", diagnostico],
                ["Indicación clínica", indicacion],
                ["Modalidad diagnóstica", modalidad],
                ["Tipo de estudio", tipo_estudio],
                ["Fecha", pd.Timestamp.now().strftime("%Y-%m-%d")],
                ["Estado del estudio", estado],
                ["Ruta Soporte", nombre_imagen_soporte],
                ["Abrir Soporte", nombre_imagen_soporte]
            ]

            df_nuevo = pd.DataFrame(datos_excel)
            nombre_excel = f"excel {p_nombre} {p_apellido}.xlsx"
            path_excel = os.path.join(CARPETA_DATOS, nombre_excel)
            df_nuevo.to_excel(path_excel, index=False, header=False)

            st.success(f"✅ ¡Estudio de TAC multi-secuencia para {p_nombre} {p_apellido} registrado correctamente!")
            
            with open(path_excel, "rb") as file_excel:
                st.download_button(
                    label="📥 Descargar Ficha Excel del Paciente",
                    data=file_excel,
                    file_name=nombre_excel,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            st.cache_data.clear()



            # Suponiendo que 'imagenes' es la lista con las imágenes de la secuencia seleccionada
num_cortes = len(imagenes)

if num_cortes > 1:
    # Crea el deslizador interactivo para cambiar de corte
    corte_index = st.slider("Seleccionar corte:", min_value=1, max_value=num_cortes, value=1) - 1
else:
    corte_index = 0

st.markdown(f"📍 **Corte actual:** {corte_index + 1} de {num_cortes}")

# Mostrar la imagen correspondiente al corte seleccionado
st.image(imagenes[corte_index], use_column_width=True)

