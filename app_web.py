import streamlit as st
import pandas as pd
import json
import fitz
import io
from PIL import Image
from google import genai
from google.genai import types
from logica_duplicidad import verificar_duplicidad

# --- INTENTO DE IMPORTACIÓN SEGURA ---
try:
    from pyzbar.pyzbar import decode
    QR_ENABLED = True
except ImportError:
    QR_ENABLED = False

st.set_page_config(page_title="FacturaFlow 360", layout="wide")

# --- 1. PORTERO DIGITAL (LOGIN) ---
def check_password():
    if "password_correct" not in st.session_state: st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔒 Acceso Restringido")
        pwd = st.text_input("Ingrese la clave de acceso al Club:", type="password")
        if st.button("Ingresar"):
            if pwd == st.secrets.get("APP_PASSWORD"):
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
        return False
    return True

# --- 2. CONFIGURACIÓN DE EMPRESA ---
def configuracion_empresa():
    st.sidebar.header("🏢 Empresa en Auditoría")
    nombre = st.sidebar.text_input("Nombre de la Empresa:")
    rnc = st.sidebar.text_input("RNC:")
    if nombre and rnc:
        st.session_state["empresa_activa"] = {"nombre": nombre, "rnc": rnc}
        st.sidebar.success(f"Auditando a: {nombre}")
        return True
    return False

# --- 3. FUNCIONES DE PROCESAMIENTO ---
def optimizar_imagen(img_bytes):
    image = Image.open(io.BytesIO(img_bytes)).convert('L')
    if image.width > 1200:
        ratio = 1200 / float(image.width)
        image = image.resize((1200, int(float(image.height) * ratio)), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=85)
    return output.getvalue(), image

def generar_formato_606(data_list):
    df = pd.DataFrame(data_list)
    formato_606 = pd.DataFrame({
        'RNC/Cedula': df.get('rnc_suplidor', ''),
        'Tipo de Bien/Servicio': '01',
        'NCF': df.get('ncf', ''),
        'Fecha Comprobante': pd.to_datetime('today').strftime('%d/%m/%Y'),
        'ITBIS Facturado': df.get('itbis', 0.0),
        'Monto Facturado': df.get('monto_total', 0.0),
        'ITBIS Retenido': 0.0,
        'Monto ITBIS a Adelantar': df.get('itbis', 0.0)
    })
    return formato_606

# --- FLUJO PRINCIPAL ---
if check_password():
    # Título dinámico
    if "empresa_activa" in st.session_state:
        st.title(f"🚀 Ingresando datos para {st.session_state['empresa_activa']['nombre']}")
    else:
        st.title("🚀 FacturaFlow 360")
    
    if configuracion_empresa():
        API_KEY = st.secrets.get("GEMINI_API_KEY")
        if "lote_facturas" not in st.session_state: st.session_state.lote_facturas = []
        
        archivo = st.file_uploader("Sube factura (PDF/Imagen)", type=["pdf", "png", "jpg"])
        
        if archivo:
            if not any(f.get("nombre_archivo") == archivo.name for f in st.session_state.lote_facturas):
                with st.spinner(f"Procesando {archivo.name}..."):
                    try:
                        doc = fitz.open(stream=archivo.read(), filetype="pdf")
                        img_bytes = doc.load_page(0).get_pixmap().pil_tobytes("png")
                        img_opt, pil_img = optimizar_imagen(img_bytes)
                        
                        data = {}
                        if QR_ENABLED:
                            try:
                                qr_data = decode(pil_img)
                                if qr_data: data = {"info": qr_data[0].data.decode('utf-8'), "metodo": "QR"}
                            except: pass
                        
                        if not data:
                            client = genai.Client(api_key=API_KEY)
                            part = types.Part.from_bytes(data=img_opt, mime_type="image/jpeg")
                            prompt = 'Extrae en JSON: {"rnc_suplidor": "", "ncf": "", "subtotal": 0.00, "itbis": 0.00, "monto_total": 0.00}'
                            response = client.models.generate_content(
                                model='gemini-2.0-flash', contents=[part, prompt],
                                config=types.GenerateContentConfig(response_mime_type="application/json")
                            )
                            data = json.loads(response.text)
                            data["metodo"] = "IA"

                        data["nombre_archivo"] = archivo.name
                        data["alerta_duplicidad"] = verificar_duplicidad(data.get("ncf"), data.get("rnc_suplidor"), st.session_state["empresa_activa"]["rnc"])
                        st.session_state.lote_facturas.append(data)
                    except Exception as e: st.error(f"Error: {e}")

        if st.session_state.lote_facturas:
            st.subheader("Auditoría de Lote")
            df_display = pd.DataFrame(st.session_state.lote_facturas)
            st.data_editor(df_display, use_container_width=True)
            
            if st.button("Exportar para DGII (Formato 606)"):
                df_606 = generar_formato_606(st.session_state.lote_facturas)
                df_606.to_excel("Reporte_606_DGII.xlsx", index=False)
                st.success("¡Archivo listo para carga masiva DGII!")
