import base64
from io import BytesIO
import glob
import os
import shutil
import zipfile
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
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

# Carpeta de datos ubicada junto a app.py.
# Así no depende de la carpeta desde la que Streamlit ejecute el programa.
DIRECTORIO_APP = os.path.dirname(os.path.abspath(__file__))
CARPETA_DATOS = os.path.join(DIRECTORIO_APP, "base_datos_dsa")
os.makedirs(CARPETA_DATOS, exist_ok=True)


def crear_respaldo_datos():
    """Empaqueta los expedientes y las imágenes para descargarlos como copia."""
    memoria = BytesIO()
    with zipfile.ZipFile(memoria, "w", compression=zipfile.ZIP_DEFLATED) as respaldo:
        for raiz, carpetas, archivos in os.walk(CARPETA_DATOS):
            carpetas[:] = [c for c in carpetas if c != "__pycache__"]
            for nombre in archivos:
                ruta = os.path.join(raiz, nombre)
                ruta_relativa = os.path.relpath(ruta, DIRECTORIO_APP)
                respaldo.write(ruta, arcname=ruta_relativa)
    memoria.seek(0)
    return memoria.getvalue()


# --- GENERAR UNA FICHA EXCEL CON EL DISEÑO SOLICITADO ---
def generar_excel_formateado(ruta_excel):
    """Crea una copia descargable de la ficha con dos columnas y estilo limpio."""
    datos = pd.read_excel(ruta_excel, header=None, dtype=str).fillna("")

    # Quitar el encabezado de búsqueda y las filas de identificación duplicadas
    # para que la ficha comience directamente con PRIMER NOMBRE, como el ejemplo.
    if len(datos) >= 3 and str(datos.iloc[0, 0]).strip().upper() == "BÚSQUEDA DE PACIENTE POR ID":
        datos = datos.iloc[3:].reset_index(drop=True)

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Ficha del paciente"
    hoja.sheet_view.showGridLines = False

    azul = PatternFill("solid", fgColor="D9E2F3")
    blanco = PatternFill("solid", fgColor="FFFFFF")
    borde = Border(
        left=Side(style="thin", color="B7B7B7"),
        right=Side(style="thin", color="B7B7B7"),
        top=Side(style="thin", color="B7B7B7"),
        bottom=Side(style="thin", color="B7B7B7"),
    )

    for indice, fila in datos.iterrows():
        etiqueta = str(fila.iloc[0]).strip() if len(fila) > 0 else ""
        valor = str(fila.iloc[1]).strip() if len(fila) > 1 else ""
        if not etiqueta and not valor:
            continue

        numero_fila = hoja.max_row + 1
        celda_etiqueta = hoja.cell(row=numero_fila, column=1, value=etiqueta)
        celda_valor = hoja.cell(row=numero_fila, column=2, value=valor)

        celda_etiqueta.fill = azul
        celda_valor.fill = blanco
        for celda in (celda_etiqueta, celda_valor):
            celda.border = borde
            celda.alignment = Alignment(
                vertical="center",
                horizontal="left",
                wrap_text=True
            )
            celda.font = Font(name="Arial", size=10, color="000000")

        celda_etiqueta.font = Font(
            name="Arial", size=9, bold=True, color="000000"
        )

        # Ajustar la altura según la longitud del contenido.
        longitud = max(len(etiqueta), len(valor))
        hoja.row_dimensions[numero_fila].height = 30 if longitud < 55 else 42

    hoja.column_dimensions["A"].width = 29
    hoja.column_dimensions["B"].width = 72
    hoja.freeze_panes = "A1"
    hoja.sheet_properties.pageSetUpPr.fitToPage = True
    hoja.page_setup.fitToWidth = 1
    hoja.page_setup.fitToHeight = 0
    hoja.page_setup.orientation = "portrait"
    hoja.page_setup.paperSize = hoja.PAPERSIZE_A4
    hoja.print_options.horizontalCentered = True
    hoja.print_area = f"A1:B{hoja.max_row}"

    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)
    return salida.getvalue()

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


# --- FUNCIÓN MEJORADA PARA CARGAR IMÁGENES Y DICOM CON BUEN CONTRASTE ---
def cargar_imagen_general(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".dcm":
        try:
            ds = pydicom.dcmread(path)
            pixel_array = ds.pixel_array.astype(float)

            # Aplicar pendiente e intercepto si existen (escala Hounsfield)
            slope = getattr(ds, "RescaleSlope", 1)
            intercept = getattr(ds, "RescaleIntercept", 0)
            pixel_array = pixel_array * slope + intercept

            # Normalización robusta con percentiles (1% y 99%)
            p_low, p_high = np.percentile(pixel_array, (1, 99))
            if p_high > p_low:
                pixel_array = np.clip(pixel_array, p_low, p_high)
                pixel_array = (
                    (pixel_array - p_low) / (p_high - p_low) * 255.0
                )
            else:
                pixel_array = np.zeros_like(pixel_array)

            pixel_array = pixel_array.astype(np.uint8)

            # Manejar inversión fotométrica (MONOCHROME1 vs MONOCHROME2)
            photometric = getattr(ds, "PhotometricInterpretation", "MONOCHROME2")
            if photometric == "MONOCHROME1":
                pixel_array = 255 - pixel_array

            img = Image.fromarray(pixel_array)
            if img.mode != "RGB":
                img = img.convert("RGB")
            return img
        except Exception as e:
            st.error(f"Error al procesar el archivo DICOM {path}: {e}")
            return None
    else:
        return Image.open(path)


# --- ASEGURAR LOS 10 PACIENTES PREDEFINIDOS ---
def asegurar_pacientes_por_defecto():
    pacientes_base = [
        {
            "excel_nombre": "excel JUAN CAMILO PEREZ.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1005837241"],
                ["ID Paciente", "1005837241"],
                ["PRIMER NOMBRE", "JUAN"],
                ["SEGUNDO NOMBRE", "CAMILO"],
                ["PRIMER APELLIDO", "PEREZ"],
                ["SEGUNDO APELLIDO", "ROJAS"],
                ["Edad", "12 años"],
                ["sexo", "M"],
                [
                    "Motivo de consulta",
                    (
                        "Dolor de tobillo derecho después de una caída durante"
                        " actividad deportiva."
                    ),
                ],
                [
                    "Síntomas principales",
                    (
                        "Dolor localizado, inflamación leve y dificultad para"
                        " caminar."
                    ),
                ],
                [
                    "Antecedentes",
                    (
                        "Sin antecedentes personales de importancia. Esquema de"
                        " vacunación completo. Sin cirugías previas."
                    ),
                ],
                [
                    "Diagnóstico presuntivo",
                    "Traumatismo de tobillo derecho.",
                ],
                ["Indicación clínica", "Descartar fractura."],
                ["Modalidad diagnóstica", "RX"],
                ["Tipo de estudio", "Radiografía de tobillo derecho"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Realizado"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel MARIA EUGENIA FANDIÑO.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1027463815"],
                ["ID Paciente", "1027463815"],
                ["PRIMER NOMBRE", "MARIA"],
                ["SEGUNDO NOMBRE", "EUGENIA"],
                ["PRIMER APELLIDO", "FANDIÑO"],
                ["SEGUNDO APELLIDO", "PACHON"],
                ["Edad", "64 años"],
                ["sexo", "F"],
                [
                    "Motivo de consulta",
                    "Cefalea reciente acompañada de mareo e inestabilidad.",
                ],
                [
                    "Síntomas principales",
                    "Cefalea, mareo y sensación de inestabilidad.",
                ],
                [
                    "Antecedentes",
                    (
                        "Hipertensión arterial diagnosticada hace 10 años, en"
                        " tratamiento farmacológico. Niega cirugías recientes."
                        " Antecedente familiar de enfermedad cerebrovascular."
                    ),
                ],
                [
                    "Diagnóstico presuntivo",
                    "Cefalea de etiología por determinar.",
                ],
                ["Indicación clínica", "Descartar alteración intracraneal."],
                ["Modalidad diagnóstica", "CT"],
                ["Tipo de estudio", "Tomografía de cráneo"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Pendiente"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel JAIRO HERNANDO CAMPOS.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1039158274"],
                ["ID Paciente", "1039158274"],
                ["PRIMER NOMBRE", "JAIRO"],
                ["SEGUNDO NOMBRE", "HERNANDO"],
                ["PRIMER APELLIDO", "CAMPOS"],
                ["SEGUNDO APELLIDO", "MORA"],
                ["Edad", "72 años"],
                ["sexo", "M"],
                [
                    "Motivo de consulta",
                    (
                        "Dolor lumbar de varios meses de evolución y dificultad"
                        " para caminar."
                    ),
                ],
                [
                    "Síntomas principales",
                    (
                        "Dolor lumbar, rigidez y parestesias ocasionales en"
                        " miembros inferiores."
                    ),
                ],
                [
                    "Antecedentes",
                    (
                        "Hipertensión arterial controlada y antecedente de"
                        " artrosis. Cirugía de rodilla hace aproximadamente 8"
                        " años. Niega trauma reciente."
                    ),
                ],
                [
                    "Diagnóstico presuntivo",
                    "Enfermedad degenerativa de columna lumbar.",
                ],
                [
                    "Indicación clínica",
                    "Resonancia magnética de columna lumbar.",
                ],
                ["Modalidad diagnóstica", "RM"],
                ["Tipo de estudio", "Resonancia de columna"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Realizado"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel LIZBETH EUGENIA TINOCO.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1056382917"],
                ["ID Paciente", "1056382917"],
                ["PRIMER NOMBRE", "LIZBETH"],
                ["SEGUNDO NOMBRE", "EUGENIA"],
                ["PRIMER APELLIDO", "TINOCO"],
                ["SEGUNDO APELLIDO", "FANDIÑO"],
                ["Edad", "36 años"],
                ["sexo", "F"],
                ["Motivo de consulta", "Dolor abdominal en hipocondrio derecho posterior a las comidas."],
                ["Síntomas principales", "Dolor abdominal, náuseas ocasionales y sensación de llenura."],
                ["Antecedentes", "Sin enfermedades crónicas conocidas. Cesárea hace 7 años. Antecedentes familiares de cálculos biliares."],
                ["Diagnóstico presuntivo", "Sospecha de enfermedad de la vesícula biliar."],
                ["Indicación clínica", "Ecografía abdominal."],
                ["Modalidad diagnóstica", "US"],
                ["Tipo de estudio", "Ecografía abdominal"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Pendiente"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel MARIA JOSE QUINTANA.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1078246359"],
                ["ID Paciente", "1078246359"],
                ["PRIMER NOMBRE", "MARIA"],
                ["SEGUNDO NOMBRE", "JOSE"],
                ["PRIMER APELLIDO", "QUINTANA"],
                ["SEGUNDO APELLIDO", ""],
                ["Edad", "15 años"],
                ["sexo", "F"],
                ["Motivo de consulta", "Dolor en miembro superior izquierdo después de traumatismo durante actividad escolar."],
                ["Síntomas principales", "Dolor, sensibilidad local y limitación del movimiento."],
                ["Antecedentes", "Sin antecedentes médicos relevantes. Sin cirugías previas. Caída deportiva menor hace 2 años, sin fracturas."],
                ["Diagnóstico presuntivo", "Traumatismo de miembro superior izquierdo. Descartar fractura o luxación."],
                ["Indicación clínica", "Radiografía del segmento afectado."],
                ["Modalidad diagnóstica", "RX"],
                ["Tipo de estudio", "Radiografía de hombro izquierdo"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Realizado"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel LAURA CAMILA SANCHEZ.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1084719263"],
                ["ID Paciente", "1084719263"],
                ["PRIMER NOMBRE", "LAURA"],
                ["SEGUNDO NOMBRE", "CAMILA"],
                ["PRIMER APELLIDO", "SANCHEZ"],
                ["SEGUNDO APELLIDO", "TORRES"],
                ["Edad", "59 años"],
                ["sexo", "F"],
                ["Motivo de consulta", "Dolor abdominal intenso de inicio reciente."],
                ["Síntomas principales", "Dolor abdominal, náuseas y malestar general."],
                ["Antecedentes", "Hipertensión arterial controlada. Antecedente de gastritis recurrente. Sin colecistectomía. Niega alergias medicamentosas conocidas."],
                ["Diagnóstico presuntivo", "Dolor abdominal agudo de etiología por determinar."],
                ["Indicación clínica", "Tomografía computarizada de abdomen."],
                ["Modalidad diagnóstica", "CT"],
                ["Tipo de estudio", "Tomografía de abdomen"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Realizado"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel JASBLEIDY TINOCO.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1096352847"],
                ["ID Paciente", "1096352847"],
                ["PRIMER NOMBRE", "JASBLEIDY"],
                ["SEGUNDO NOMBRE", ""],
                ["PRIMER APELLIDO", "TINOCO"],
                ["SEGUNDO APELLIDO", "FANDIÑO"],
                ["Edad", "50 años"],
                ["sexo", "F"],
                ["Motivo de consulta", "Dolor persistente en hombro derecho y limitación para elevar el brazo."],
                ["Síntomas principales", "Dolor, disminución de movilidad y molestias con movimientos repetitivos."],
                ["Antecedentes", "Sin enfermedades crónicas importantes. Antecedente de tendinitis del hombro izquierdo hace 4 años. Actividad laboral con movimientos repetitivos."],
                ["Diagnóstico presuntivo", "Lesión del manguito rotador por determinar."],
                ["Indicación clínica", "Resonancia magnética de hombro derecho."],
                ["Modalidad diagnóstica", "RM"],
                ["Tipo de estudio", "Resonancia hombro derecho"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Pendiente"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel LIZ MADELEINE RAMIREZ.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1019274638"],
                ["ID Paciente", "1019274638"],
                ["PRIMER NOMBRE", "LIZ"],
                ["SEGUNDO NOMBRE", "MADELEINE"],
                ["PRIMER APELLIDO", "RAMIREZ"],
                ["SEGUNDO APELLIDO", "RAMIREZ"],
                ["Edad", "55 años"],
                ["sexo", "F"],
                ["Motivo de consulta", "Control preventivo y evaluación de tejido mamario."],
                ["Síntomas principales", "Molestia mamaria ocasional sin signos inflamatorios."],
                ["Antecedentes", "Hipertensión arterial controlada. Madre con antecedente de cáncer de mama. Una cesárea. Sin antecedentes personales de cáncer."],
                ["Diagnóstico presuntivo", "Evaluación mamaria preventiva."],
                ["Indicación clínica", "Mamografía bilateral de tamizaje."],
                ["Modalidad diagnóstica", "MG"],
                ["Tipo de estudio", "Mamografía"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Pendiente"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel DOUGLAS CEDIEL.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1045827196"],
                ["ID Paciente", "1045827196"],
                ["PRIMER NOMBRE", "DOUGLAS"],
                ["SEGUNDO NOMBRE", ""],
                ["PRIMER APELLIDO", "CEDIEL"],
                ["SEGUNDO APELLIDO", ""],
                ["Edad", "53 años"],
                ["sexo", "M"],
                ["Motivo de consulta", "Tos persistente, dificultad respiratoria y dolor torácico leve."],
                ["Síntomas principales", "Tos, disnea leve y dolor torácico ocasional."],
                ["Antecedentes", "Antecedente de tabaquismo durante aproximadamente 15 años, suspendido hace 5 años. Hipertensión arterial controlada. Episodios previos de bronquitis."],
                ["Diagnóstico presuntivo", "Alteración respiratoria por determinar."],
                ["Indicación clínica", "Radiografía de tórax."],
                ["Modalidad diagnóstica", "RX"],
                ["Tipo de estudio", "Radiografía de torax"],
                ["Fecha", "18/08/2026"],
                ["Estado del estudio", "Realizado"],
                ["Ruta Soporte", "No disponible"],
                ["Abrir Soporte", "No disponible"],
            ],
        },
        {
            "excel_nombre": "excel LADY TATIANA ARROYO.xlsx",
            "datos": [
                ["BÚSQUEDA DE PACIENTE POR ID", None],
                ["ID Paciente:", "1063748152"],
                ["ID Paciente", "1063748152"],
                ["PRIMER NOMBRE", "LADY"],
                ["SEGUNDO NOMBRE", "TATIANA"],
                ["PRIMER APELLIDO", "ARROYO"],
                ["SEGUNDO APELLIDO", "CABEZAS"],
                ["Edad", "31 años"],
                ["sexo", "F"],
                ["Motivo de consulta", "Dolor pélvico intermitente y cambios recientes en el ciclo menstrual."],
                ["Síntomas principales", "Dolor pélvico, ciclos irregulares y molestias abdominales ocasionales."],
                ["Antecedentes", "Sin enfermedades crónicas conocidas. Antecedente de quiste ovárico funcional diagnosticado hace 3 años, resuelto con manejo médico. Sin cirugías ginecológicas."],
                ["Diagnóstico presuntivo", "Alteración ginecológica por determinar."],
                ["Indicación clínica", "Ecografía pélvica."],
                ["Modalidad diagnóstica", "US"],
                ["Tipo de estudio", "Ecografía pélvica"],
                ["Fecha", "18/08/2026"],
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

    st.caption("Copia de seguridad de pacientes e imágenes")
    if st.button("🗜️ Preparar copia de seguridad", use_container_width=True):
        try:
            st.session_state["respaldo_datos_zip"] = crear_respaldo_datos()
            st.success("Copia preparada. Descárgala para conservarla en tu equipo.")
        except Exception as error:
            st.error(f"No se pudo preparar la copia: {error}")

    if st.session_state.get("respaldo_datos_zip"):
        st.download_button(
            "📥 Descargar copia de seguridad",
            data=st.session_state["respaldo_datos_zip"],
            file_name="respaldo_visualizador_dsa.zip",
            mime="application/zip",
            use_container_width=True,
        )

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
                    excel_formateado = generar_excel_formateado(p["archivo"])
                    nombre_archivo_excel = os.path.basename(p["archivo"])
                    st.download_button(
                            label="📥 Descargar Ficha Excel Actual",
                            data=excel_formateado,
                            file_name=nombre_archivo_excel,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )

                # --- MÓDULO DE EDICIÓN Y GESTIÓN DE SECUENCIAS (DICOM / IMÁGENES) ---
                with st.expander("✏️ Editar Paciente / Gestionar Secuencias"):
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
                        st.write(
                            "📁 **Agregar más imágenes o secuencia DICOM (.dcm):**"
                        )
                        nuevas_imgs = st.file_uploader(
                            "Subir archivos adicionales (JPG/PNG/DICOM .dcm):",
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
                            st.info("No hay archivos adicionales para eliminar.")

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
                                os.makedirs(dir_estudio_ges, exist_ok=True)
                                for idx_img, img_f in enumerate(nuevas_imgs):
                                    ext = os.path.splitext(img_f.name)[
                                        1
                                    ].lower()
                                    path_dest = os.path.join(
                                        dir_estudio_ges,
                                        f"secuencia_adicional_{idx_img+1}_{pd.Timestamp.now().strftime('%H%M%S')}{ext}",
                                    )
                                    with open(path_dest, "wb") as f_img:
                                        f_img.write(img_f.getbuffer())

                            st.success(
                                "¡Información y secuencia actualizadas con éxito!"
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
                    "🖼️ Visor de Secuencia DICOM e Imágenes del Paciente"
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

                    col_sel, col_del_sec = st.columns([3, 1])

                    with col_sel:
                        img_elegida_nombre = st.selectbox(
                            "📂 Seleccione la imagen o archivo DICOM de la secuencia:",
                            nombres_archivos,
                            key=f"sel_img_{cedula_final}",
                        )

                    img_sel_path = todas_las_imagenes[
                        nombres_archivos.index(img_elegida_nombre)
                    ]

                    with col_del_sec:
                        st.write("")
                        st.write("")
                        if st.button(
                            "🗑️ Eliminar secuencia",
                            key=f"btn_del_sec_{img_elegida_nombre}_{cedula_final}",
                            type="secondary",
                        ):
                            if os.path.exists(img_sel_path):
                                os.remove(img_sel_path)
                                st.success(
                                    f"Secuencia '{img_elegida_nombre}' eliminada con éxito."
                                )
                                st.cache_data.clear()
                                st.rerun()

                    # Cargar mediante la función mejorada
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
                        f"⚠️ No hay archivos o secuencias cargadas para el paciente: {p['nombre']}"
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
        st.subheader("🧠 Carga de Imágenes o Archivos DICOM de la Secuencia")
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
                    ext = os.path.splitext(img_file.name)[1].lower()
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
                f"✅ ¡Estudio y secuencia DICOM para {p_nombre} {p_apellido} guardados correctamente!"
            )

            excel_formateado = generar_excel_formateado(path_excel)
            st.download_button(
                    label="📥 Descargar Ficha Excel del Paciente",
                    data=excel_formateado,
                    file_name=nombre_excel,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            st.cache_data.clear()

