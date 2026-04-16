# ==================== 2. MODELO FLEXIBLE (Fix ValidationError) ====================
class FinatrixData(BaseModel):
    # Todos los campos ahora aceptan None y tienen valor por defecto 0.0
    ingresos_totales: Optional[float] = 0.0
    costo_ventas: Optional[float] = 0.0
    gastos_operativos: Optional[float] = 0.0
    utilidad_neta: Optional[float] = 0.0
    activos_corrientes: Optional[float] = 0.0
    activos_totales: Optional[float] = 0.0
    pasivos_corrientes: Optional[float] = 0.0
    pasivos_totales: Optional[float] = 0.0
    patrimonio: Optional[float] = 0.0

def calcular_metricas(d: FinatrixData):
    # Usamos .get() o acceso directo porque Pydantic ya aseguró que son floats o 0.0
    ing = d.ingresos_totales or 0.0
    ebitda = ing - (d.costo_ventas or 0.0) - (d.gastos_operativos or 0.0)
    
    # Evitamos división por cero con una guardia simple
    def div(n, d): return n / d if d and d != 0 else 0
    
    r = {
        "ebitda": ebitda,
        "liquidez_corriente": div(d.activos_corrientes, d.pasivos_corrientes),
        "roe": div(d.utilidad_neta, d.patrimonio) * 100,
        "endeudamiento": div(d.pasivos_totales, d.activos_totales) * 100,
    }
    
    # Score con lógica de umbrales
    pts = 30
    pts += 25 if r["liquidez_corriente"] >= 1.1 else -10
    pts += 25 if r["ebitda"] > 0 else -20
    pts += 20 if r["endeudamiento"] < 70 else 5
    
    r["finatrix_score"] = int(max(0, min(100, pts)))
    return r

# ==================== 4. UI CON ESCUDO DE DATOS ====================
# ... (mantén tu código anterior de extracción de texto e IA) ...

if archivo:
    if st.button("🚀 Iniciar Auditoría"):
        with st.spinner("Analizando con escudo de datos..."):
            texto = extraer_texto(archivo)
            if not texto: st.stop()
                
            datos_raw, diagnostico = analizar_con_ia(texto, client)
            
            # --- EL ESCUDO (Sanitización Radical) ---
            datos_limpios = {}
            for campo in FinatrixData.model_fields:
                valor = datos_raw.get(campo)
                
                if valor is None or str(valor).lower() in ['null', 'none', 'nan', '']:
                    datos_limpios[campo] = 0.0
                elif isinstance(valor, (int, float)):
                    datos_limpios[campo] = float(valor)
                elif isinstance(valor, str):
                    # Quitamos todo lo que no sea número, punto o signo menos
                    import re
                    solo_numeros = re.sub(r'[^\d.-]', '', valor.replace(',', '.'))
                    try:
                        datos_limpios[campo] = float(solo_numeros)
                    except:
                        datos_limpios[campo] = 0.0
                else:
                    datos_limpios[campo] = 0.0

            # Ahora sí, instanciamos sin miedo al ValidationError
            try:
                data_instancia = FinatrixData(**datos_limpios)
                ratios = calcular_metricas(data_instancia)
                
                # ... (resto de tu UI de métricas y PDF) ...
                st.success("✅ Análisis procesado exitosamente")
                
            except Exception as e:
                st.error(f"Error crítico en la validación: {e}")
                st.info("Sugerencia: Revisa que el documento tenga cifras numéricas claras.")
