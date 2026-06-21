# --- LOGICA PRINCIPAL ---
if check_password():
    # --- CAMBIO AQUÍ: Título dinámico ---
    if "empresa_activa" in st.session_state:
        nombre_empresa = st.session_state["empresa_activa"]["nombre"]
        st.title(f"🚀 Ingresando datos para {nombre_empresa}")
    else:
        st.title("🚀 FacturaFlow 360")
    
    if configuracion_empresa():
        # ... resto de tu código
