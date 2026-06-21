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

# --- 2. ESTACIÓN DE TRABAJO (CONFIGURACIÓN) ---
def configuracion_empresa():
    st.sidebar.header("🏢 Empresa en Auditoría")
    nombre = st.sidebar.text_input("Nombre de la Empresa:")
    rnc = st.sidebar.text_input("RNC:")
    
    if nombre and rnc:
        st.session_state["empresa_activa"] = {"nombre": nombre, "rnc": rnc}
        st.sidebar.success(f"Auditando a: {nombre}")
        return True
    else:
        st.info("Por favor, ingresa el Nombre y RNC de la empresa para comenzar a trabajar.")
        return False

# --- LOGICA PRINCIPAL ---
if check_password():
    st.title("🚀 FacturaFlow 360")
    
    if configuracion_empresa():
        API_KEY = st.secrets.get("GEMINI_API_KEY")
        if "lote_facturas" not in st.session_state: st.session_state.lote_facturas = []
        
        archivo = st.file_uploader("Sube factura (PDF/Imagen)", type=["pdf", "png", "jpg"])
        
        # ... (aquí mantienes la misma lógica de procesamiento que teníamos)
        # Asegúrate de usar st.session_state["empresa_activa"]["rnc"] para la validación de duplicidad
