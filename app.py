import streamlit as st
import pandas as pd
import json
from PIL import Image
import google.generativeai as genai

st.set_page_config(page_title="Lector Contable Gratuito", layout="wide")
st.title("📄 Generador de Asientos Contables Gratis")

# Clave gratuita de Google Gemini AI
gemini_key = st.text_input("Ingresa tu API Key GRATUITA de Google Gemini (AIzaSy...)", type="password")
st.caption("Consigue tu clave 100% gratis en: https://aistudio.google.com/app/apikey")

archivo = st.file_uploader("Sube una foto o imagen de tu Factura, Boleta o RH", type=["png", "jpg", "jpeg"])

if archivo and gemini_key:
    if st.button("Procesar Documento"):
        with st.spinner("Analizando comprobante con IA de Google..."):
            try:
                # Configurar clave API de Gemini
                genai.configure(api_key=gemini_key.strip())
                
                # Intentar usar gemini-1.5-flash directamente
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                except Exception:
                    model = genai.GenerativeModel('gemini-1.5-pro')

                # Cargar imagen con PIL
                image = Image.open(archivo)

                prompt = """Analiza este comprobante de pago peruano (Factura, Boleta o Recibo por Honorarios). 
                Extrae los datos y responde ÚNICAMENTE en formato JSON válido sin texto adicional ni bloques de código markdown:
                {
                    "tipo_documento": "FACTURA",
                    "ruc_emisor": "20123456789",
                    "razon_social": "NOMBRE EMPRESA S.A.C.",
                    "serie_numero": "F001-1234",
                    "subtotal": 100.00,
                    "igv": 18.00,
                    "retencion": 0.00,
                    "total": 118.00
                }"""

                response = model.generate_content([prompt, image])

                # Limpieza de la respuesta JSON
                raw_text = response.text.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()

                datos = json.loads(raw_text)

                st.success("✅ Documento procesado correctamente")
                
                # --- Lógica de Asientos Contables según el tipo de documento ---
                tipo = str(datos.get("tipo_documento", "FACTURA")).upper()
                subtotal = float(datos.get("subtotal") or 0)
                igv = float(datos.get("igv") or 0)
                total = float(datos.get("total") or 0)
                retencion = float(datos.get("retencion") or 0)

                if "RH" in tipo or "HONORARIOS" in tipo:
                    asiento_data = [
                        {"Cuenta": "6321 - Honorarios Profesionales", "Debe": total + retencion, "Haber": 0},
                        {"Cuenta": "40172 - Retenciones 4ta Categoría", "Debe": 0, "Haber": retencion},
                        {"Cuenta": "4699 - Otras Cuentas por Pagar", "Debe": 0, "Haber": total}
                    ]
                else: # Facturas / Boletas de Compras
                    asiento_data = [
                        {"Cuenta": "6011 - Mercaderías / Gastos", "Debe": subtotal, "Haber": 0},
                        {"Cuenta": "40111 - IGV Cuenta Propia", "Debe": igv, "Haber": 0},
                        {"Cuenta": "4212 - Emitidas en Cartera", "Debe": 0, "Haber": total}
                    ]

                df_asiento = pd.DataFrame(asiento_data)

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Datos Extraídos")
                    st.json(datos)
                with col2:
                    st.subheader("Asiento Contable Generado")
                    st.dataframe(df_asiento, hide_index=True)

                    # Exportar a CSV / Excel rápido
                    csv = df_asiento.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Asiento (CSV/Excel)",
                        data=csv,
                        file_name=f"asiento_{datos.get('serie_numero', 'comprobante')}.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"Error al procesar el documento: {e}")
