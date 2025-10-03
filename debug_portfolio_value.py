#!/usr/bin/env python3

import pandas as pd
import numpy as np
from portfolio_calculator import PortfolioCalculator

# Cargar datos
try:
    # Cargar operaciones
    operaciones = pd.read_excel('operaciones.xlsx', sheet_name='Operaciones')
    
    # Mapear columnas a formato esperado
    operaciones_mapped = pd.DataFrame()
    operaciones_mapped['Fecha'] = operaciones['Fecha']
    operaciones_mapped['Tipo'] = operaciones['Operacion']
    operaciones_mapped['Activo'] = operaciones['Activo']
    operaciones_mapped['Cantidad'] = operaciones['Nominales']
    operaciones_mapped['Precio_Concertacion'] = operaciones['Precio']
    operaciones_mapped['Monto'] = operaciones['Valor']
    
    # Limpiar datos
    operaciones_mapped['Tipo'] = operaciones_mapped['Tipo'].replace('nan', np.nan)
    operaciones_mapped['Tipo'] = operaciones_mapped['Tipo'].str.strip()
    operaciones_mapped['Activo'] = operaciones_mapped['Activo'].str.strip()
    
    # Para cupones y amortizaciones, llenar NaN en cantidad y precio con 0
    cupon_mask = operaciones_mapped['Tipo'].str.strip().str.lower().str.contains('cupon', na=False)
    amortization_mask = operaciones_mapped['Tipo'].str.strip().str.lower().str.contains('amortizacion', na=False)
    special_ops_mask = cupon_mask | amortization_mask
    
    operaciones_mapped.loc[special_ops_mask, 'Cantidad'] = operaciones_mapped.loc[special_ops_mask, 'Cantidad'].fillna(0)
    operaciones_mapped.loc[special_ops_mask, 'Precio_Concertacion'] = operaciones_mapped.loc[special_ops_mask, 'Precio_Concertacion'].fillna(0)
    
    # Eliminar filas con NaN en columnas críticas
    operaciones_mapped = operaciones_mapped.dropna(subset=['Fecha', 'Tipo', 'Activo', 'Monto'])
    
    # Cargar precios
    precios = pd.read_excel('operaciones.xlsx', sheet_name='Precios')
    
    # La primera columna debe ser las fechas
    fecha_col = precios.columns[0]
    precios = precios.rename(columns={fecha_col: 'Fecha'})
    
    # Convertir a formato largo (melt)
    precios_long = precios.melt(
        id_vars=['Fecha'], 
        var_name='Activo', 
        value_name='Precio'
    )
    precios_long = precios_long.dropna()  # Eliminar filas con NaN
    precios_long['Fecha'] = pd.to_datetime(precios_long['Fecha'])
    precios_long['Activo'] = precios_long['Activo'].str.strip()
    
    # Convertir fechas
    operaciones_mapped['Fecha'] = pd.to_datetime(operaciones_mapped['Fecha'])
    
    print("=== DATOS CARGADOS ===")
    print(f"Operaciones: {len(operaciones_mapped)} filas")
    print(f"Precios: {len(precios_long)} filas")
    
    print("\n=== OPERACIONES ===")
    for _, op in operaciones_mapped.iterrows():
        print(f"{op['Fecha'].strftime('%Y-%m-%d')}: {op['Tipo']} {op['Activo']} - Cantidad: {op['Cantidad']}, Precio: {op['Precio_Concertacion']}, Monto: {op['Monto']}")
    
    # Crear calculador con fecha de inicio 2025-09-05
    start_date = pd.to_datetime('2025-09-05')
    calculator = PortfolioCalculator(operaciones_mapped, precios_long, start_date)
    
    # Calcular valor de cartera
    portfolio_data = calculator.calculate_portfolio_value()
    
    print("\n=== VALORES DE CARTERA ===")
    # Mostrar valores alrededor del 5-6 sep
    sep_data = portfolio_data[
        (portfolio_data['Fecha'] >= pd.to_datetime('2025-09-04')) & 
        (portfolio_data['Fecha'] <= pd.to_datetime('2025-09-07'))
    ]
    
    for _, row in sep_data.iterrows():
        print(f"{row['Fecha'].strftime('%Y-%m-%d')}: {row['Valor_Cartera']:.2f}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
