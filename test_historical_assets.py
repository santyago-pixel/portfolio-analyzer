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
    
    # Probar con fecha de inicio que incluye activos vendidos
    # Usar fecha del 10 de septiembre (después de que se vendió el activo 'a')
    start_date = pd.to_datetime('2025-09-10')
    print(f"\n=== PRUEBA CON FECHA DE INICIO: {start_date.strftime('%Y-%m-%d')} ===")
    print("El activo 'a' fue vendido el 13-sep, pero debería aparecer en la atribución")
    
    calculator = PortfolioCalculator(operaciones_mapped, precios_long, start_date)
    
    # Calcular análisis de atribución
    attribution = calculator.calculate_attribution_analysis()
    
    print(f"\n=== ANÁLISIS DE ATRIBUCIÓN ===")
    if not attribution.empty:
        for _, row in attribution.iterrows():
            print(f"{row['Activo']}: Valor Actual: {row['Valor_Actual']:.2f}, Cantidad: {row['Cantidad']:.0f}, Inversión Total: {row['Inversion_Total']:.2f}")
    else:
        print("No hay datos de atribución")
    
    # Verificar que el activo 'a' aparece aunque fue vendido
    asset_a = attribution[attribution['Activo'] == 'a']
    if not asset_a.empty:
        print(f"\n✅ El activo 'a' aparece en la atribución (fue vendido pero tuvo operaciones en el período)")
        print(f"   Cantidad actual: {asset_a['Cantidad'].iloc[0]:.0f}")
        print(f"   Inversión total: {asset_a['Inversion_Total'].iloc[0]:.2f}")
    else:
        print(f"\n❌ El activo 'a' NO aparece en la atribución (debería aparecer)")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
