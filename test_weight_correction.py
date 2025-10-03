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
    
    print("=== PRUEBA DE CORRECCIÓN DE PESOS ===")
    print("Problema: Activos vendidos tenían peso 0%")
    print("Solución: Peso basado en inversión total")
    print()
    
    # Probar con fecha de inicio que incluye activos vendidos
    start_date = pd.to_datetime('2025-09-10')
    print(f"=== PRUEBA CON FECHA DE INICIO: {start_date.strftime('%Y-%m-%d')} ===")
    print("El activo 'a' fue vendido el 13-sep, pero ahora debería tener peso > 0%")
    print()
    
    calculator = PortfolioCalculator(operaciones_mapped, precios_long, start_date)
    
    # Calcular análisis de atribución
    attribution = calculator.calculate_attribution_analysis()
    
    print("=== RESULTADOS CON CORRECCIÓN ===")
    if not attribution.empty:
        total_weight = 0
        for _, row in attribution.iterrows():
            print(f"{row['Activo']}: Peso: {row['Peso']:.1%}, Contribución: {row['Contribucion']:.1%}, Inversión: ${row['Inversion_Total']:.2f}")
            total_weight += row['Peso']
        
        print(f"\nSuma de pesos: {total_weight:.1%}")
        print()
        
        # Verificar que el activo 'a' ahora tiene peso > 0%
        asset_a = attribution[attribution['Activo'] == 'a']
        if not asset_a.empty:
            weight_a = asset_a['Peso'].iloc[0]
            if weight_a > 0:
                print(f"✅ CORRECCIÓN EXITOSA: El activo 'a' ahora tiene peso {weight_a:.1%}")
                print(f"   Inversión total: ${asset_a['Inversion_Total'].iloc[0]:.2f}")
                print(f"   Contribución: {asset_a['Contribucion'].iloc[0]:.1%}")
            else:
                print(f"❌ ERROR: El activo 'a' sigue teniendo peso {weight_a:.1%}")
        else:
            print(f"❌ ERROR: El activo 'a' no aparece en la atribución")
    else:
        print("No hay datos de atribución")
    
    print()
    print("=== COMPARACIÓN DE MÉTODOS ===")
    print("Método anterior (problemático):")
    print("  - Peso = Valor actual / Valor total cartera")
    print("  - Activos vendidos: peso = 0%")
    print()
    print("Método nuevo (correcto):")
    print("  - Peso = Inversión total activo / Inversión total cartera")
    print("  - Activos vendidos: peso proporcional a su inversión histórica")
    print("  - Los pesos suman exactamente 100%")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
