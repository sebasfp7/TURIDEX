import pandas as pd

def calcular_ratios_financieros(datos_extraidos):
    """
    Toma un diccionario de datos extraídos por la IA y calcula ratios reales.
    """
    try:
        # Extraer valores base del diccionario generado por la IA
        ingresos = float(datos_extraidos.get("ingresos_totales", 0))
        costos = float(datos_extraidos.get("costo_ventas", 0))
        gastos_op = float(datos_extraidos.get("gastos_operativos", 0))
        activos = float(datos_extraidos.get("activos_totales", 0))
        pasivos = float(datos_extraidos.get("pasivos_totales", 0))
        
        # Cálculos de Ratios (Lógica Humana Inmune a Alucinaciones)
        utilidad_bruta = ingresos - costos
        margen_bruto = (utilidad_bruta / ingresos * 100) if ingresos > 0 else 0
        
        ebitda = ingresos - costos - gastos_op
        margen_ebitda = (ebitda / ingresos * 100) if ingresos > 0 else 0
        
        ratio_solvencia = activos / pasivos if pasivos > 0 else 0
        capital_trabajo = activos - pasivos

        # Interpretación automática
        salud = "Estable"
        if margen_ebitda < 10 or ratio_solvencia < 1.2:
            salud = "Crítica"
        elif margen_ebitda > 25 and ratio_solvencia > 2:
            salud = "Excelente"

        return {
            "margen_bruto": round(margen_bruto, 2),
            "margen_ebitda": round(margen_ebitda, 2),
            "ratio_solvencia": round(ratio_solvencia, 2),
            "capital_trabajo": round(capital_trabajo, 2),
            "salud_general": salud
        }
    except Exception as e:
        return {"error": f"Fallo en cálculo: {str(e)}"}
