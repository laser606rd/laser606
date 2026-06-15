import streamlit as st
import pandas as pd
import json
import fitz
from google import genai
from google.genai import types

# Importamos las funciones desde nuestro archivo separado
from logica_duplicidad import verificar_duplicidad, registrar_en_historial

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Laser606 | Club Exclusivo", layout="wide")

# Llave maestra/código de acceso para esta versión Beta Cerrado
CODIGO_VALIDO = "LIDER606"

if "lote_facturas" not in st.session_state:
    st.session_state.lote_facturas = []
if "ingreso_club" not in st.session_state:
    st.session_state.ingreso_club = False

def validar_factura(f):
    errores = []
    if not f.get("rnc_suplidor"): 
        errores.append("RNC Suplidor faltante")
    if not f.get("ncf"): 
        errores.append("NCF faltante")
    return errores

# --- MOTOR DE PROCESAMIENTO ---
def procesar_con_ia(archivo, api_key, rnc_empresa):
    try:
        client = genai.Client(api_key=api_key)
        doc = fitz.open(stream=archivo.read(), filetype="pdf")
        img_bytes = doc.load_page(0).get_pixmap().pil_tobytes("png")
        
        part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        prompt = (
            "Extrae datos fiscales (JSON), usando exactamente estas llaves en minúsculas:\n"
            "{\n"
            '  "rnc_suplidor": "RNC o cédula del proveedor, sin guiones",\n'
            '  "rnc_comprador": "RNC de la empresa que compra/recibe el servicio o bien, sin guiones",\n'
            '  "ncf": "código completo del NCF",\n'
            '  "fecha": "AAAAMMDD",\n'
            '  "monto_total": 0.00,\n'
            '  "itbis": 0.00\n'
            "}"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[part, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        extracted = json.loads(response.text)
        extracted["id"] = len(st.session_state.lote_facturas) + 1
        extracted["nombre_archivo"] = archivo.name
        
        rnc_en_factura = extracted.get("rnc_comprador", "")
        if rnc_en_factura and str(rnc_en_factura).strip() != str(rnc_empresa).strip():
            extracted["alerta"] = f"⚠️ ¡Alerta! Esta factura está emitida a nombre del RNC {rnc_en_factura}, no de la empresa actual ({rnc_empresa})."
        else:
            extracted["alerta"] = verificar_duplicidad(extracted.get("ncf"), extracted.get("rnc_suplidor"), rnc_empresa)
            
        return extracted
    except Exception as e:
        st.sidebar.error(f"Error procesando: {str(e)}")
        return None

# --- FLUJO: CLUB EXCLUSIVO (BIENVENIDA) ---
if not st.session_state.ingreso_club:
    st.markdown("<h1 style='text-align: center; color: #2C3E50;'>⚡ Laser606 System</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #34495E;'>El Club Exclusivo</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px;'>La comunidad privada de contadores dominicanos que eliminan el 100% de los errores en sus reportes fiscales 606.</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        codigo_ingreso = st.text_input("🗝️ Ingresa tu código de invitación:", type="password", placeholder="Escribe tu llave de acceso")
        if st.button("Ingresar al Club", type="primary", use_container_width=True):
            if codigo_ingreso.strip() == CODIGO_VALIDO:
                st.session_state.ingreso_club = True
                st.rerun()
            else:
                st.error("Código de invitación inválido. Solicítalo a un miembro activo del club.")
            
    st.markdown("<br><hr>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🔒 Auditoría Blindada")
        st.caption("Revisión exhaustiva libre de errores humanos.")
    with c2:
        st.markdown("### ✨ Reportes Perfectos")
        st.caption("Estructura exacta validada para la DGII.")
    with c3:
        st.markdown("### 🚫 Cero Multas DGII")
        st.caption("Protección total ante duplicidades y anomalías.")

# --- FLUJO: APLICACIÓN PURA (AUDITORÍA 606) ---
else:
    # --- NAVEGACIÓN LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.title("⚡ Laser606 - Élite")
        st.markdown("---")
        st.header("⚙️ Configuración Fiscal")
        rnc_empresa = st.text_input("🏢 RNC de la Empresa:")
        api_key_input = st.text_input("🔑 Google AI Studio API Key:", type="password")
        periodo_actual = st.text_input("📅 Período Fiscal:", value="202606")
        st.markdown("---")
        if st.button("🚪 Salir del Club"):
            st.session_state.ingreso_club = False
            st.rerun()

    st.title("⚡ Laser606 - Módulo de Auditoría Fiscal (606)")

    if not rnc_empresa or not api_key_input:
        st.warning("Por favor, ingresa el RNC de la empresa y tu API Key en la barra lateral para acceder a la herramienta.")
        st.stop()

    archivos = st.file_uploader("📥 Arrastra tus facturas (PDFs)", accept_multiple_files=True, type=["pdf"])

    if archivos and api_key_input:
        nombres_proc = [f["nombre_archivo"] for f in st.session_state.lote_facturas]
        nuevos = [a for a in archivos if a.name not in nombres_proc]
        if nuevos:
            for a in nuevos:
                res = procesar_con_ia(a, api_key_input, rnc_empresa)
                if res: 
                    st.session_state.lote_facturas.append(res)
            st.rerun()

    if st.session_state.lote_facturas:
        st.subheader(f"📋 Lote de auditoría para empresa: {rnc_empresa}")
        for idx, f in enumerate(st.session_state.lote_facturas):
            errs = validar_factura(f)
            with st.container(border=True):
                if f.get('alerta'): 
                    st.error(f.get('alerta'))
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"### Factura #{f.get('id', idx+1)}")
                    st.caption(f"📁 {f.get('nombre_archivo', 'Archivo')}")
                    if errs:
                        for e in errs: 
                            st.error(e)
                    else: 
                        st.success("✅ Validación Estructural Aprobada")
                with col2:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        f["rnc_suplidor"] = st.text_input("RNC Suplidor", value=str(f.get("rnc_suplidor", "")), key=f"rnc_{idx}")
                        f["ncf"] = st.text_input("NCF", value=str(f.get("ncf", "")), key=f"ncf_{idx}")
                    with col_b:
                        f["monto_total"] = st.number_input("Total", value=float(f.get("monto_total", 0)), key=f"tot_{idx}")
                        f["itbis"] = st.number_input("ITBIS", value=float(f.get("itbis", 0)), key=f"itb_{idx}")

        if st.button("🚀 Finalizar: Registrar y Exportar Excel", type="primary"):
            hay_alertas = any(f.get('alerta') for f in st.session_state.lote_facturas)
            
            if hay_alertas:
                st.error("🚨 ¡Acción bloqueada! Tienes facturas con alertas activas (RNC incorrecto o NCF duplicado). Debes corregir o eliminar dichas facturas antes de poder registrar o exportar el reporte.")
            else:
                for f in st.session_state.lote_facturas:
                    registrar_en_historial(f.get('ncf', ''), f.get('rnc_suplidor', ''), periodo_actual, rnc_empresa)
                df = pd.DataFrame(st.session_state.lote_facturas)
                df.to_excel(f"Reporte_606_{rnc_empresa}.xlsx", index=False)
                st.success(f"Reporte generado para {rnc_empresa} y facturas registradas en el sistema local.")