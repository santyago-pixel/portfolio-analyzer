#!/usr/bin/env python3
"""
Script para verificar que los cupones se detectan correctamente
"""

import pandas as pd
import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from portfolio_calculator import PortfolioCalculator

def test_coupon_detection():
    """Probar detección de cupones con datos similares a los del usuario"""
    
    # Datos de prueba que simulan el archivo del usuario
    operaciones_data = [
        {'Fecha': '2024-09-01', 'Tipo': 'Compra', 'Activo': 'A', 'Cantidad': 100, 'Precio_Concertacion': 1.0, 'Monto': 100.0},
        {'Fecha': '2024-09-10', 'Tipo': 'Cupon', 'Activo': 'A', 'Cantidad': 0, 'Precio_Concertacion': 0, 'Monto': 3.0},  # Este es el cupón que debe detectarse
        {'Fecha': '2024-09-15', 'Tipo': 'Compra', 'Activo': 'B', 'Cantidad': 50, 'Precio_Concertacion': 2.0, 'Monto': 100.0},
    ]
    
    precios_data = [
        {'Fecha': '2024-09-01', 'Activo': 'A', 'Precio': 1.0},
        {'Fecha': '2024-09-10', 'Activo': 'A', 'Precio': 1.1},
        {'Fecha': '2024-09-15', 'Activo': 'A', 'Precio': 1.2},
        {'Fecha': '2024-09-01', 'Activo': 'B', 'Precio': 2.0},
        {'Fecha': '2024-09-15', 'Activo': 'B', 'Precio': 2.1},
    ]
    
    operaciones_df = pd.DataFrame(operaciones_data)
    precios_df = pd.DataFrame(precios_data)
    
    print("=== VERIFICACIÓN DE DETECCIÓN DE CUPONES ===")
    print(f"Operaciones cargadas: {len(operaciones_df)}")
    print("\nOperaciones:")
    for i, row in operaciones_df.iterrows():
        print(f"  {i+1}. {row['Fecha']} - {row['Tipo']} - {row['Activo']} - Monto: {row['Monto']}")
    
    print("\n=== CREANDO CALCULADORA ===")
    calculator = PortfolioCalculator(operaciones_df, precios_df)
    
    print("\n=== ANÁLISIS DE ATRIBUCIÓN ===")
    attribution = calculator.calculate_attribution_analysis()
    
    print("\nResultados del análisis de atribución:")
    for _, row in attribution.iterrows():
        print(f"Activo: {row['Activo']}")
        print(f"  Ingresos por Cupones/Dividendos: {row['Ingresos_Cupones_Dividendos']}")
        print(f"  Ganancias Realizadas: {row['Ganancias_Realizadas']}")
        print(f"  Retorno Total: {row['Retorno_Total']:.4f}")
        print()
    
    # Verificar específicamente el cupón del activo A
    activo_a = attribution[attribution['Activo'] == 'A']
    if not activo_a.empty:
        cupones_a = activo_a.iloc[0]['Ingresos_Cupones_Dividendos']
        if cupones_a == 3.0:
            print("✅ ÉXITO: El cupón de 3.0 del activo A se detectó correctamente")
        else:
            print(f"❌ ERROR: Se esperaba 3.0, pero se encontró {cupones_a}")
    else:
        print("❌ ERROR: No se encontró el activo A en el análisis")
    
    return attribution

if __name__ == "__main__":
    test_coupon_detection()
