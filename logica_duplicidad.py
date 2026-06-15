import os
import json

ARCHIVO_HISTORIAL = "historial_ncf.json"

def cargar_historial():
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "r") as f:
                return json.load(f)
        except: 
            return {}
    return {}

def verificar_duplicidad(ncf, rnc_suplidor, rnc_empresa):
    if not ncf or not rnc_suplidor: 
        return None
    historial = cargar_historial()
    key = f"{rnc_empresa}_{rnc_suplidor}_{ncf}"
    if key in historial: 
        return f"⚠️ NCF {ncf} ya reportado para esta empresa."
    return None

def registrar_en_historial(ncf, rnc_suplidor, periodo, rnc_empresa):
    historial = cargar_historial()
    historial[f"{rnc_empresa}_{rnc_suplidor}_{ncf}"] = periodo
    with open(ARCHIVO_HISTORIAL, "w") as f:
        json.dump(historial, f, indent=4)