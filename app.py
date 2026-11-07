import base64
import glob
import os
import shutil
import numpy as np
import pandas as pd
import pydicom
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageEnhance, ImageOps

# 1. Configuración de la página web Streamlit
st.set_page_config(
    page_title="Visualizador DSA",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Carpeta fija y persistente para almacenar todos los expedientes
CARPETA_DATOS = "base_datos_dsa"
os.makedirs(CARPETA_DATOS, exist_ok=True)

USUARIOS_VALIDOS = {
    "darhienn": "1995",
    "Darhienn": "1995",
    "darien": "1995",
    "Darien": "1995",
    "admin": "pacs2026",
    "medico": "radiologia123",
}


def inicializar_sesion():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = None


inicializar_sesion()

if not st.session_state.autenticado:

    def obtener_base64_imagen(ruta_imagen):
        try:
            with open(ruta_imagen, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except Exception:
            return ""

    img_base64 = obtener_base64_imagen("fondo.jpg")
    if img_base64:
        background_style = (
            f'background-image: url("data:image/jpeg;base64,{img_base64}");'
        )
    else:
        background_style = "background-color: #0e1117;"

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
        unsafe_allow_html=True,
    )

    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("form_login"):
            st.subheader("🔐 Iniciar Sesión")
            usr = st.text_input("Usuario:").strip()
            pwd = st.text_input("Contraseña:", type="password").strip()
            btn_login = st.form_submit_button(
                "Ingresar al Sistema", use_container_width=True
            )

            if btn_login:
                if usr in USUARIOS_VALIDOS and USUARIOS_VALIDOS[usr] == pwd:
                    st.session_state.autenticado = True
                    st.session_state.usuario = usr
                    st.success("✅ Acceso concedido. Cargando sistema...")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()


# --- FUNCIÓN PARA CARGAR IMÁGENES NORMALES O DICOM (.dcm) ---
def cargar_imagen_general(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".dcm":
        try:
            ds = pydicom.dcmread(path)
            pixel_array = ds.pixel_array
            # Normalizar los valores de píxeles a rango 0-255 (uint8)
            if pixel_array.max() != pixel_array.min():
                pixel_array = (
                    (pixel_array - pixel_array.min())
                    / (pixel_array.max() - pixel_array.min())
                    * 255.0
                )
            pixel_array = pixel_array.astype(np.uint8)
            img = Image.fromarray(pixel_array)
            if img.mode != "RGB":
                img = img.convert("RGB")
            return img
        except Exception as e:
            st.error(f"Error al procesar el archivo DICOM {path}: {e}")
            return None
    else:
        return Image.open(path)


# --- ASEGURAR LOS 3 PACIENTES PRINCIPALES POR DEFECTO ---
def asegurar_pacientes_por_defecto():
    pacientes_base = [
        {
            "excel_nombre": "excel Maria Eugenia.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "101010"],
                ["ID Paciente", "101010"],
                ["PRIMER NOMBRE", "Maria"],
                ["SEGUNDO NOMBRE", "Eugenia"],
                ["PRIMER APELLIDO", "Perez"],
                ["SEGUNDO APELLIDO", ""],
                ["Edad", "45 años"],
                ["sexo", "F"],
                ["Motivo de consulta", "Control médico general"],
                ["Síntomas principales", "Ninguno"],
                ["Antecedentes", "Ninguno"],
                ["Diagnóstico presuntivo", "Sano"],
                ["Indicación clínica", "Control"],
                ["Modalidad diagnóstica", "RX"],
                ["Tipo de estudio", "Rayos X de Tórax"],
                ["Fecha", pd.Timestamp.now().strftime("%Y-%m-%d")],
                ["Estado del estudio", "Realizado"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel Jairo Campos.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "202020"],
                ["ID Paciente", "202020"],
                ["PRIMER NOMBRE", "Jairo"],
                ["SEGUNDO NOMBRE", ""],
                ["PRIMER APELLIDO", "Campos"],
                ["SEGUNDO APELLIDO", ""],
                ["Edad", "50 años"],
                ["sexo", "M"],
                ["Motivo de consulta", "Dolor lumbar"],
                ["Síntomas principales", "Lumbalgia"],
                ["Antecedentes", "Lumbalgia crónica"],
                ["Diagnóstico presuntivo", "Espondilosis"],
                ["Indicación clínica", "Evaluación de columna"],
                ["Modalidad diagnóstica", "TAC"],
                ["Tipo de estudio", "TAC de columna lumbar"],
                ["Fecha", pd.Timestamp.now().strftime("%Y-%m-%d")],
                ["Estado del estudio", "Realizado"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel Juan Camilo.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "303030"],
                ["ID Paciente", "303030"],
                ["PRIMER NOMBRE", "Juan"],
                ["SEGUNDO NOMBRE", "Camilo"],
                ["PRIMER APELLIDO", "Gomez"],
                ["SEGUNDO APELLIDO", ""],
                ["Edad", "30 años"],
                ["sexo", "M"],
                ["Motivo de consulta", "Traumatismo en rodilla"],
                ["Síntomas principales", "Dolor e inflamación"],
                ["Antecedentes", "Deportista"],
                ["Diagnóstico presuntivo", "Posible esguince"],
                ["Indicación clínica", "Estudio articular"],
                ["Modalidad diagnóstica", "RM"],
                ["Tipo de estudio", "Resonancia de Rodilla"],
                ["Fecha", pd.Timestamp.now().strftime("%Y-%m-%d")],
                ["Estado del estudio", "Realizado"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
    ]

    for p in pacientes_base:
        path_excel = os.path.join(CARPETA_DATOS, p["excel_nombre"])
        if not os.path.exists(path_excel):
            df = pd.DataFrame(p["datos"])
            df.to_excel(path_excel, index=False, header=False)


# Ejecutar la verificación al iniciar
asegurar_pacientes_por_defecto()


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
                        val_str = (
                            str(int(val))
                            if isinstance(val, (int, float))
                            else str(val).strip()
                        )
                        if val_str and val_str.lower() != "nan":
                            id_paciente = val_str
                            break

            if id_paciente:
                id_paciente = id_paciente.replace(" ", "").replace(".0", "")

                p_nombre = info.get(
                    "PRIMER NOMBRE", info.get("PRIEMER NOMBRE", "")
                )
                s_nombre = info.get("SEGUNDO NOMBRE", "")
                p_apellido = info.get("PRIMER APELLIDO", "")
                s_apellido = info.get("SEGUNDO APELLIDO", "")

                nombre_completo = (
                    f"{p_nombre} {s_nombre} {p_apellido} {s_apellido}".strip()
                )
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
                    "ruta_imagen": info.get("Ruta Soporte", ""),
                }
        except Exception as e:
            st.error(f"Error procesando {archivo}: {e}")

    return pacientes


with st.sidebar:
    st.write(f"👤 **Usuario activo:** `{st.session_state.usuario.upper()}`")
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.usuario = None
        st.rerun()
    st.divider()

tab_buscar, tab_nuevo = st.tabs(
    ["🔍 Consultar Paciente y Visor PACS", "➕ Registrar Nuevo Paciente"]
)

pacientes = cargar_todos_los_pacientes(CARPETA_DATOS)


with tab_buscar:
    st.sidebar.header("📋 Historias Registradas")

    opcion_lista = "-- Seleccionar de la lista --"
    if pacientes:
        opciones = {
            f"{p['id']} - {p['nombre']}": p["id"] for p in pacientes.values()
        }
        seleccion_combo = st.sidebar.selectbox(
            "Seleccione un paciente:", [opcion_lista] + list(opciones.keys())
        )
    else:
        st.sidebar.warning("No se encontraron archivos de pacientes.")
        seleccion_combo = opcion_lista

    cedula_escrita = st.text_input(
        "🔍 Ingrese o busque la Cédula del Paciente:"
    ).strip().replace(" ", "")

    cedula_final = ""
    if cedula_escrita:
        cedula_final = cedula_escrita
    elif seleccion_combo != opcion_lista:
        cedula_final = opciones[seleccion_combo]

    if cedula_final:
        if cedula_final in pacientes:
            p = pacientes[cedula_final]
            st.success(
                f"**Paciente:** {p['nombre']} | **Cédula:** {cedula_final} | **Modalidad:** {p['modalidad']} | **Estudio:** {p['estudio']}"
            )

            col_info, col_visor = st.columns([1, 2])

            with col_info:
                st.subheader("📋 Datos del Registro RIS")
                st.write(f"**Edad / Sexo:** {p['edad']} | {p['sexo']}")
                st.write(f"**Tipo de Estudio:** {p['estudio']}")
                st.write(f"**Estado del Estudio:** {p['estado']}")
                st.write(f"**Motivo Consulta:** {p['motivo']}")
                st.write(f"**Diagnóstico Presuntivo:** {p['diagnostico']}")

                # --- BOTÓN DE DESCARGA RÁPIDA DE EXCEL ---
                st.divider()
                st.subheader("📥 Ficha del Paciente")
                if os.path.exists(p["archivo"]):
                    with open(p["archivo"], "rb") as f_excel:
                        nombre_archivo_excel = os.path.basename(p["archivo"])
                        st.download_button(
                            label="📥 Descargar Ficha Excel Actual",
                            data=f_excel,
                            file_name=nombre_archivo_excel,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )

                # --- MÓDULO DE EDICIÓN, AGREGAR Y ELIMINAR IMÁGENES/DICOM ---
                with st.expander("✏️ Editar Paciente / Gestionar Archivos"):
                    with st.form(f"form_editar_{cedula_final}"):
                        nuevo_estado = st.selectbox(
                            "Modificar Estado del Estudio:",
                            ["Realizado", "Pendiente", "En proceso"],
                            index=(
                                ["Realizado", "Pendiente", "En proceso"].index(
                                    p["estado"]
                                )
                                if p["estado"]
                                in ["Realizado", "Pendiente", "En proceso"]
                                else 0
                            ),
                        )
                        nuevo_diagnostico = st.text_input(
                            "Actualizar Diagnóstico Presuntivo:",
                            value=p["diagnostico"],
                        )

                        st.markdown("---")
                        st.write("📁 **Agregar más imágenes o archivos DICOM:**")
                        nuevas_imgs = st.file_uploader(
                            "Subir archivos nuevos (JPG/PNG/DICOM .dcm):",
                            type=["jpg", "jpeg", "png", "bmp", "dcm"],
                            accept_multiple_files=True,
                            key=f"add_{cedula_final}",
                        )

                        st.markdown("---")
                        st.write("🗑️ **Eliminar archivos existentes:**")

                        dir_estudio_ges = os.path.join(
                            CARPETA_DATOS, f"estudio_{cedula_final}"
                        )
                        paths_actuales_ges = []
                        if os.path.exists(dir_estudio_ges) and os.path.isdir(
                            dir_estudio_ges
                        ):
                            for root, dirs, files in os.walk(dir_estudio_ges):
                                for file in files:
                                    if file.lower().endswith(
                                        (".jpg", ".jpeg", ".png", ".bmp", ".dcm")
                                    ):
                                        paths_actuales_ges.append(
                                            os.path.join(root, file)
                                        )

                        imgs_a_borrar = []
                        if paths_actuales_ges:
                            nombres_ges = {
                                os.path.basename(path): path
                                for path in paths_actuales_ges
                            }
                            imgs_a_borrar = st.multiselect(
                                "Seleccione los archivos que desea eliminar:",
                                options=list(nombres_ges.keys()),
                                key=f"del_{cedula_final}",
                            )
                        else:
                            st.info(
                                "No hay archivos adicionales en la carpeta para eliminar."
                            )

                        btn_guardar_cambios = st.form_submit_button(
                            "💾 Guardar Cambios"
                        )

                        if btn_guardar_cambios:
                            df_existente = pd.read_excel(
                                p["archivo"], header=None
                            )
                            for idx, row in df_existente.iterrows():
                                k_val = str(row[0]).strip().lower()
                                if k_val == "estado del estudio":
                                    df_existente.at[idx, 1] = nuevo_estado
                                elif k_val == "diagnóstico presuntivo":
                                    df_existente.at[idx, 1] = nuevo_diagnostico

                            df_existente.to_excel(
                                p["archivo"], index=False, header=False
                            )

                            if paths_actuales_ges and imgs_a_borrar:
                                for nom_img in imgs_a_borrar:
                                    path_a_eliminar = nombres_ges.get(nom_img)
                                    if path_a_eliminar and os.path.exists(
                                        path_a_eliminar
                                    ):
                                        os.remove(path_a_eliminar)

                            if nuevas_imgs:
                                os.makedirs(dir_estudio, exist_ok=True)
                                for idx_img, img_f in enumerate(nuevas_imgs):
                                    ext = os.path.splitext(img_f.name)[1]
                                    path_dest = os.path.join(
                                        dir_estudio_ges,
                                        f"archivo_adicional_{idx_img+1}_{pd.Timestamp.now().strftime('%H%M%S')}{ext}",
                                    )
                                    with open(path_dest, "wb") as f_img:
                                        f_img.write(img_f.getbuffer())

                            st.success(
                                "¡Información y archivos actualizados con éxito!"
                            )
                            st.cache_data.clear()
                            st.rerun()

                st.divider()
                st.subheader("⚙️ Herramientas de Visualización")
                brillo = st.slider("Brillo", 0.2, 3.0, 1.0, 0.1)
                contraste = st.slider("Contraste", 0.2, 3.0, 1.0, 0.1)
                invertir = st.checkbox(
                    "Invertir Colores (Negativo Radiológico)"
                )
                rotacion = st.selectbox("Rotación (°)", [0, 90, 180, 270])
                ancho = st.slider("Escala / Zoom (px)", 300, 1000, 600, 50)

                st.divider()
                if st.button(
                    "🗑️ Eliminar este Paciente del Sistema", type="primary"
                ):
                    if os.path.exists(p["archivo"]):
                        os.remove(p["archivo"])
                    carpeta_estudio_del = os.path.join(
                        CARPETA_DATOS, f"estudio_{p['id']}"
                    )
                    if os.path.exists(carpeta_estudio_del):
                        shutil.rmtree(carpeta_estudio_del, ignore_errors=True)
                    ruta_img_del = os.path.join(
                        CARPETA_DATOS, p["ruta_imagen"]
                    )
                    if os.path.exists(ruta_img_del) and os.path.isfile(
                        ruta_img_del
                    ):
                        os.remove(ruta_img_del)

                    st.success(
                        f"Ficha de {p['nombre']} eliminada correctamente."
                    )
                    st.cache_data.clear()
                    st.rerun()

            with col_visor:
                st.subheader(
                    "🖼️ Visor de Imágenes y Estudios DICOM del Paciente"
                )

                carpeta_estudio = os.path.join(
                    CARPETA_DATOS, f"estudio_{p['id']}"
                )
                todas_las_imagenes = []

                if os.path.exists(carpeta_estudio) and os.path.isdir(
                    carpeta_estudio
                ):
                    for root, dirs, files in os.walk(carpeta_estudio):
                        for file in files:
                            if file.lower().endswith(
                                (".jpg", ".jpeg", ".png", ".bmp", ".dcm")
                            ):
                                todas_las_imagenes.append(
                                    os.path.join(root, file)
                                )

                if not todas_las_imagenes:
                    ruta_principal = os.path.join(
                        CARPETA_DATOS, p["ruta_imagen"]
                    )
                    if os.path.exists(ruta_principal) and os.path.isfile(
                        ruta_principal
                    ):
                        todas_las_imagenes.append(ruta_principal)

                if todas_las_imagenes:
                    todas_las_imagenes = sorted(todas_las_imagenes)
                    nombres_archivos = [
                        os.path.basename(path) for path in todas_las_imagenes
                    ]

                    img_elegida_nombre = st.selectbox(
                        "📂 Seleccione la imagen o archivo DICOM a visualizar:",
                        nombres_archivos,
                    )
                    img_sel_path = todas_las_imagenes[
                        nombres_archivos.index(img_elegida_nombre)
                    ]

                    # Cargar mediante función compatible con JPG y DICOM
                    img = cargar_imagen_general(img_sel_path)

                    if img is not None:
                        if invertir:
                            if img.mode == "RGBA":
                                r, g, b, a = img.split()
                                rgb_img = Image.merge("RGB", (r, g, b))
                                inv = ImageOps.invert(rgb_img)
                                r, g, b = inv.split()
                                img = Image.merge("RGBA", (r, g, b, a))
                            else:
                                img = ImageOps.invert(img.convert("RGB"))

                        if rotacion != 0:
                            img = img.rotate(-rotacion, expand=True)

                        img = ImageEnhance.Brightness(img).enhance(brillo)
                        img = ImageEnhance.Contrast(img).enhance(contraste)

                        st.image(
                            img,
                            width=ancho,
                            caption=f"Visualizando: {img_elegida_nombre}",
                        )
                else:
                    st.warning(
                        f"⚠️ No hay archivos o imágenes cargadas para el paciente: {p['nombre']}"
                    )

                # --- BOTÓN DE ELIMINAR PACIENTE ADICIONAL EN EL VISOR ---
                st.divider()
                if st.button(
                    "🗑️ Eliminar este Paciente (Desde el Visor)",
                    type="primary",
                    key=f"btn_del_visor_{cedula_final}",
                ):
                    if os.path.exists(p["archivo"]):
                        os.remove(p["archivo"])
                    carpeta_estudio_del = os.path.join(
                        CARPETA_DATOS, f"estudio_{p['id']}"
                    )
                    if os.path.exists(carpeta_estudio_del):
                        shutil.rmtree(carpeta_estudio_del, ignore_errors=True)
                    ruta_img_del = os.path.join(
                        CARPETA_DATOS, p["ruta_imagen"]
                    )
                    if os.path.exists(ruta_img_del) and os.path.isfile(
                        ruta_img_del
                    ):
                        os.remove(ruta_img_del)

                    st.success(
                        f"Ficha de {p['nombre']} eliminada correctamente."
                    )
                    st.cache_data.clear()
                    st.rerun()


with tab_nuevo:
    st.header("📝 Formulario de Registro Clínico con Soporte DICOM")
    st.write(
        "Diligencie los datos y cargue las imágenes o archivos DICOM (.dcm) del estudio médico."
    )

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
            modalidad = st.selectbox(
                "Modalidad Diagnóstica",
                ["CT", "TAC", "RX", "RM", "US", "OTRO"],
            )
            tipo_estudio = st.text_input(
                "Tipo de Estudio (Ej: TAC de Cráneo Simple)",
                value="TAC de Cráneo",
            )
            estado = st.selectbox(
                "Estado del Estudio", ["Realizado", "Pendiente", "En proceso"]
            )

        st.divider()
        st.subheader("🧠 Carga de Imágenes o Archivos DICOM")
        archivos_imagenes = st.file_uploader(
            "Seleccione las imágenes o archivos DICOM (puede elegir varios a la vez)",
            type=["jpg", "jpeg", "png", "bmp", "dcm"],
            accept_multiple_files=True,
        )

        boton_guardar = st.form_submit_button("💾 Guardar Paciente en el Sistema")

    if boton_guardar:
        if not id_paciente or not p_nombre or not p_apellido:
            st.error(
                "⚠️ Complete los campos obligatorios (Cédula, Primer Nombre y Primer Apellido)."
            )
        else:
            nombre_imagen_soporte = "No disponible: el estudio está pendiente"
            dir_estudio = os.path.join(CARPETA_DATOS, f"estudio_{id_paciente}")
            os.makedirs(dir_estudio, exist_ok=True)

            primer_archivo_global = None

            if archivos_imagenes:
                for idx, img_file in enumerate(archivos_imagenes):
                    ext = os.path.splitext(img_file.name)[1]
                    filename = f"imagen_{idx+1}{ext}"
                    path_dest = os.path.join(dir_estudio, filename)
                    with open(path_dest, "wb") as f:
                        f.write(img_file.getbuffer())
                    if not primer_archivo_global:
                        primer_archivo_global = filename

            if primer_archivo_global:
                nombre_imagen_soporte = primer_archivo_global
                src_first = os.path.join(dir_estudio, primer_archivo_global)
                if os.path.exists(src_first):
                    # Si es DICOM principal, intentamos convertir una vista previa JPG para compatibilidad del sistema
                    ext_first = os.path.splitext(src_first)[1].lower()
                    if ext_first == ".dcm":
                        img_prev = cargar_imagen_general(src_first)
                        if img_prev:
                            path_jpg_principal = os.path.join(
                                CARPETA_DATOS,
                                f"{p_apellido}_{id_paciente}_principal.jpg",
                            )
                            img_prev.save(path_jpg_principal, "JPEG")
                            nombre_imagen_soporte = (
                                f"{p_apellido}_{id_paciente}_principal.jpg"
                            )
                    else:
                        img_data_bytes = open(src_first, "rb").read()
                        with open(
                            os.path.join(
                                CARPETA_DATOS,
                                f"{p_apellido}_{id_paciente}_principal.jpg",
                            ),
                            "wb",
                        ) as f:
                            f.write(img_data_bytes)
                        nombre_imagen_soporte = (
                            f"{p_apellido}_{id_paciente}_principal.jpg"
                        )

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
                ["Abrir Soporte", nombre_imagen_soporte],
            ]

            df_nuevo = pd.DataFrame(datos_excel)
            nombre_excel = f"excel {p_nombre} {p_apellido}.xlsx"
            path_excel = os.path.join(CARPETA_DATOS, nombre_excel)
            df_nuevo.to_excel(path_excel, index=False, header=False)

            st.success(
                f"✅ ¡Estudio (con soporte DICOM) para {p_nombre} {p_apellido} guardado correctamente!"
            )

            with open(path_excel, "rb") as file_excel:
                st.download_button(
                    label="📥 Descargar Ficha Excel del Paciente",
                    data=file_excel,
                    file_name=nombre_excel,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            st.cache_data.clear()
            
