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
API_KEY = st.secrets.get("GEMINI_API_KEY")

if "lote_facturas" not in st.session_state: st.session_state.lote_facturas = []

st.title("🚀 FacturaFlow 360 - Auditoría Fiscal Ágil")
rnc_empresa = st.sidebar.text_input("RNC de la Empresa:")

def optimizar_imagen(img_bytes):
    image = Image.open(io.BytesIO(img_bytes)).convert('L')
    if image.width > 1200:
        ratio = 1200 / float(image.width)
        image = image.resize((1200, int(float(image.height) * ratio)), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=85)
    return output.getvalue(), image

if API_KEY and rnc_empresa:
    archivo = st.file_uploader("Sube factura (PDF/Imagen)", type=["pdf", "png", "jpg"])
    if archivo:
        if not any(f["nombre_archivo"] == archivo.name for f in st.session_state.lote_facturas):
            with st.spinner(f"Procesando {archivo.name}..."):
                try:
                    doc = fitz.open(stream=archivo.read(), filetype="pdf")
                    img_bytes = doc.load_page(0).get_pixmap().pil_tobytes("png")
                    img_opt, pil_img = optimizar_imagen(img_bytes)
                    
                    data = {}
                    # Usamos QR solo si está disponible y funciona
                    if QR_ENABLED:
                        try:
                            qr_data = decode(pil_img)
                            if qr_data:
                                data = {"info": qr_data[0].data.decode('utf-8'), "metodo": "QR"}
                        except:
                            QR_ENABLED = False
                    
                    # Si no hay QR o falló, usamos IA
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
                    data["alerta_duplicidad"] = verificar_duplicidad(data.get("ncf"), data.get("rnc_suplidor"), rnc_empresa)
                    st.session_state.lote_facturas.append(data)
                except Exception as e:
                    st.error(f"Error procesando: {e}")

    if st.session_state.lote_facturas:
        st.subheader("Auditoría de Lote")
        edited_df = st.data_editor(pd.DataFrame(st.session_state.lote_facturas), use_container_width=True)
        if st.button("Exportar Excel"):
            edited_df.to_excel("FacturaFlow_Reporte.xlsx", index=False)
            st.success("¡Exportado!")
