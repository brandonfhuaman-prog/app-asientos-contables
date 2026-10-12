import streamlit as st
import pandas as pd
import json
import base64
from huggingface_hub import InferenceClient

st.set_page_config(page_title="Lector Contable Gratuito", layout="wide")
st.title("📄 Generador de Asientos Contables Gratis")

# Clave gratuita de Hugging Face
hf_token = st.text_input("Ingresa tu Token GRATUITO de Hugging Face (hf_...)", type="password")
st.caption("Consigue tu token gratis en: https://huggingface.co/settings/tokens")

archivo = st.file_uploader("Sube una foto o imagen de tu Factura, Boleta o RH", type=["png", "jpg", "jpeg"])

if archivo and hf_token:
    # Convertir imagen a base64
    bytes_data = archivo.getvalue()
    base64_image = base64.b64encode(bytes_data).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{base64_image}"

    if st.button("Procesar Documento"):
        with st.spinner("Analizando comprobante con IA gratuita..."):
            try:
                client = InferenceClient(api_key=hf_token)

                prompt = """Analiza este comprobante de pago (Factura, Boleta o Recibo por Honorarios). 
                Extrae los datos y responde ÚNICAMENTE en formato JSON válido sin texto adicional:
                {
                    "tipo_documento": "FACTURA" o "BOLETA" o "RH",
                    "ruc_emisor": "numero de ruc",
                    "razon_social": "nombre emisor",
                    "serie_numero": "ej: F001-1234",
                    "subtotal": 0.00,
                    "igv": 0.00,
                    "retencion": 0.00,
                    "total": 0.00
                }"""

                response = client.chat.completions.create(
                    model="Qwen/Qwen2-VL-7B-Instruct",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": data_url}},
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ],
                    max_tokens=500
                )

                # Limpieza de la respuesta para obtener JSON puro
                raw_text = response.choices[0].message.content.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()

                datos = json.loads(raw_text)

                st.success("✅ Documento procesado correctamente")
                
                # --- Lógica de Asientos Contables según el tipo de documento ---
                tipo = datos.get("tipo_documento", "FACTURA").upper()
                subtotal = float(datos.get("subtotal") or 0)
                igv = float(datos.get("igv") or 0)
                total = float(datos.get("total") or 0)
                retencion = float(datos.get("retencion") or 0)

                asiento_data = []

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

            except Exception as e:
                st.error(f"Error al procesar: {e}")
