from pydantic import BaseModel, Field, validator
from typing import Optional

class DatosFinancieros(BaseModel):
    # --- Datos Crudos (Inputs) ---
    ingresos_totales: float = Field(ge=0)
    costo_ventas: float = Field(ge=0)
    gastos_operativos: float = Field(ge=0)
    utilidad_neta: float
    
    activos_corrientes: float = Field(ge=0)
    activos_totales: float = Field(ge=0)
    pasivos_corrientes: float = Field(ge=0)
    pasivos_totales: float = Field(ge=0)
    patrimonio: float = Field(ge=0)
    inventarios: float = Field(default=0, ge=0)

    # --- Ratios de Liquidez (Cálculos automáticos) ---
    @property
    def ratio_corriente(self):
        return self.activos_corrientes / self.pasivos_corrientes if self.pasivos_corrientes > 0 else 0

    @property
    def prueba_acida(self):
        return (self.activos_corrientes - self.inventarios) / self.pasivos_corrientes if self.pasivos_corrientes > 0 else 0

    # --- Ratios de Rentabilidad ---
    @property
    def margen_ebitda(self):
        ebitda = self.ingresos_totales - self.costo_ventas - self.gastos_operativos
        return (ebitda / self.ingresos_totales) * 100 if self.ingresos_totales > 0 else 0

    @property
    def roe(self):
        return (self.utilidad_neta / self.patrimonio) * 100 if self.patrimonio > 0 else 0
