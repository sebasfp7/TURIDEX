from pydantic import BaseModel, Field

class DatosFinancieros(BaseModel):
    ingresos_totales: float = Field(ge=0, description="Ingresos brutos")
    costo_ventas: float = Field(ge=0)
    gastos_operativos: float = Field(ge=0)
    activos_totales: float = Field(ge=0)
    pasivos_totales: float = Field(ge=0)
    patrimonio: float = Field(ge=0)
    
    # Aquí puedes añadir más campos según tu lista de 20+ ratios
