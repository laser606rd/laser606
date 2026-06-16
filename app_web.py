import streamlit as st
import pandas as pd
import json
import fitz
import concurrent.futures # ¡NUEVO!
from google import genai
from google.genai import types

# Importamos las funciones desde nuestro archivo separado
from logica_duplicidad import verificar_duplicidad, registrar_en_historial

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Laser606 | Club Exclusivo", layout="wide")

CODIGO_VALIDO = "LIDER606"
API_KEY_MAESTRA = st.secrets.get("GEMINI_API_KEY", "")

if "lote_facturas" not in st.session_state:
    st.session_state.lote_facturas = []
if "ingreso_club" not in st.session_state:
    st.session_state.ingreso_club = False

def validar_factura(f):
    errores = []
    if not f.get("rnc_suplidor"): errores.append("RNC Suplidor faltante")
    if not f.get("ncf"): errores.append("NCF faltante")
    return errores

def procesar_con_ia(archivo, api_key, rnc_empresa):
    try:
        client = genai.Client(api_key=api_key)
        doc = fitz.open(stream=archivo.read(), filetype="pdf")
        img_bytes = doc.load_page(0).get_pixmap().pil_tobytes("png")
        
        part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        prompt = 'Extrae en JSON (minúsculas): {"rnc_suplidor": "", "rnc_comprador": "", "ncf": "", "fecha": "", "monto_total": 0.00, "itbis": 0.00}'
        
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Usamos flash para máxima velocidad
            contents=[part, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        extracted = json.loads(response.text)
        extracted["nombre_archivo"] = archivo.name
        rnc_en_factura = extracted.get("rnc_comprador", "")
        if rnc_en_factura and str(rnc_en_factura).strip() != str(rnc_empresa).strip():
            extracted["alerta"] = f"⚠️ RNC {rnc_en_factura} no coincide con {rnc_empresa}."
        else:
            extracted["alerta"] = verificar_duplicidad(extracted.get("ncf"), extracted.get("rnc_suplidor"), rnc_empresa)
        return extracted
    except Exception:
        return None

# --- UI ---
if not st.session_state.ingreso_club:
    st.markdown("<h1 style='text-align: center;'>⚡ Laser606 System</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        codigo_ingreso = st.text_input("🗝️ Ingresa tu código:", type="password")
        if st.button("Ingresar"):
            if codigo_ingreso.strip() == CODIGO_VALIDO:
                st.session_state.ingreso_club = True
                st.rerun()
else:
    with st.sidebar:
        st.title("⚡ Laser606 - Élite")
        rnc_empresa = st.text_input("🏢 RNC de la Empresa:")
        nombre_empresa = st.text_input("📝 Nombre de la Empresa:")
        periodo_actual = st.text_input("📅 Período Fiscal:", value="202606")
        if st.button("🚪 Salir"):
            st.session_state.ingreso_club = False
            st.rerun()

    if nombre_empresa:
        st.title(f"📋 Registraremos facturas para: {nombre_empresa}")
    else:
        st.title("⚡ Laser606 - Auditoría Fiscal")

    if not API_KEY_MAESTRA or not rnc_empresa:
        st.error("Configura API Key en Secrets y RNC en barra lateral.")
        st.stop()

    archivos = st.file_uploader("📥 Arrastra PDFs", accept_multiple_files=True, type=["pdf"])

    if archivos:
        nombres_proc = [f["nombre_archivo"] for f in st.session_state.lote_facturas]
        nuevos = [a for a in archivos if a.name not in nombres_proc]
        if nuevos:
            progress_bar = st.progress(0)
            status_text = st.empty()
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(procesar_con_ia, a, API_KEY_MAESTRA, rnc_empresa): a for a in nuevos}
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    res = future.result()
                    if res: st.session_state.lote_facturas.append(res)
                    status_text.text(f"Procesando: {i+1} de {len(nuevos)}")
                    progress_bar.progress((i + 1) / len(nuevos))
            st.rerun()

    for idx, f in enumerate(st.session_state.lote_facturas):
        with st.container(border=True):
            if f.get('alerta'): st.error(f.get('alerta'))
            col_a, col_b = st.columns(2)
            with col_a:
                f["ncf"] = st.text_input("NCF", value=str(f.get("ncf", "")), key=f"ncf_{idx}")
            with col_b:
                f["monto_total"] = st.number_input("Total", value=float(f.get("monto_total", 0)), key=f"tot_{idx}")
    
    if st.button("🚀 Finalizar y Exportar"):
        df = pd.DataFrame(st.session_state.lote_facturas)
        df.to_excel(f"Reporte_{rnc_empresa}.xlsx", index=False)
        st.success("Reporte generado.")
