#!/usr/bin/env python3
"""
Script de prueba para verificar el debug del portfolio_calculator
"""

import pandas as pd
from portfolio_calculator import PortfolioCalculator

# Crear datos de prueba
operaciones_data = [
    {'Fecha': '2024-09-01', 'Tipo': 'Compra', 'Activo': 'A', 'Cantidad': 100, 'Precio_Concertacion': 1.0, 'Monto': 100.0},
    {'Fecha': '2024-09-10', 'Tipo': 'Cupon', 'Activo': 'A', 'Cantidad': 0, 'Precio_Concertacion': 0, 'Monto': 3.0},
]

precios_data = [
    {'Fecha': '2024-09-01', 'Activo': 'A', 'Precio': 1.0},
    {'Fecha': '2024-09-10', 'Activo': 'A', 'Precio': 1.1},
]

operaciones_df = pd.DataFrame(operaciones_data)
precios_df = pd.DataFrame(precios_data)

print("=== INICIANDO PRUEBA DE DEBUG ===")
print(f"Operaciones de prueba: {len(operaciones_df)}")
print(operaciones_df)

print("\n=== CREANDO CALCULADORA ===")
calculator = PortfolioCalculator(operaciones_df, precios_df)

print("\n=== CALCULANDO ANÁLISIS DE ATRIBUCIÓN ===")
attribution = calculator.calculate_attribution_analysis()
print(attribution)

print("\n=== PRUEBA COMPLETADA ===")
