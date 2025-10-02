"""
Módulo para cálculos avanzados de cartera de inversión
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class PortfolioCalculator:
    """Calculadora avanzada de métricas de cartera"""
    
    def __init__(self, operaciones: pd.DataFrame, precios: pd.DataFrame):
        self.operaciones = operaciones.copy()
        self.precios = precios.copy()
        self.portfolio_data = None
        self.daily_returns = None
        self.metrics = None
        
        # Procesar datos
        self._process_data()
    
    def _process_data(self):
        """Procesar y limpiar los datos de entrada"""
        # Convertir fechas
        self.operaciones['Fecha'] = pd.to_datetime(self.operaciones['Fecha'])
        
        # Normalizar nombres de columnas de operaciones
        if 'Operacion' in self.operaciones.columns and 'Tipo' not in self.operaciones.columns:
            self.operaciones['Tipo'] = self.operaciones['Operacion']
        if 'Nominales' in self.operaciones.columns and 'Cantidad' not in self.operaciones.columns:
            self.operaciones['Cantidad'] = self.operaciones['Nominales']
        if 'Valor' in self.operaciones.columns and 'Monto' not in self.operaciones.columns:
            self.operaciones['Monto'] = self.operaciones['Valor']
        
        # Procesar precios (estructura: fechas en columna A, activos en fila 1)
        if 'Activo' in self.precios.columns and 'Precio' in self.precios.columns:
            # Formato largo: Fecha, Activo, Precio
            self.precios['Fecha'] = pd.to_datetime(self.precios['Fecha'])
            self.precios = self.precios.sort_values('Fecha')
        else:
            # Formato ancho: fechas en columna A, activos en fila 1
            # Asegurar que la primera columna sea 'Fecha'
            if self.precios.columns[0] != 'Fecha':
                fecha_col = self.precios.columns[0]  # Primera columna (fechas)
                self.precios = self.precios.rename(columns={fecha_col: 'Fecha'})
            
            self.precios['Fecha'] = pd.to_datetime(self.precios['Fecha'])
            
            # Convertir a formato largo (melt)
            self.precios = self.precios.melt(
                id_vars=['Fecha'], 
                var_name='Activo', 
                value_name='Precio'
            )
            self.precios = self.precios.dropna()  # Eliminar filas con NaN
            self.precios = self.precios.sort_values('Fecha')
        
        # Ordenar operaciones por fecha
        self.operaciones = self.operaciones.sort_values('Fecha')
        
        # Crear índice de fechas únicas
        self.date_range = pd.date_range(
            start=self.precios['Fecha'].min(),
            end=self.precios['Fecha'].max(),
            freq='D'
        )
    
    def calculate_portfolio_value(self) -> pd.DataFrame:
        """Calcular el valor de la cartera por día"""
        portfolio_values = []
        
        for date in self.date_range:
            # Obtener operaciones hasta esta fecha
            ops_until_date = self.operaciones[self.operaciones['Fecha'] <= date]
            
            # Calcular posición actual de cada activo
            positions = {}
            cash_flow = 0
            
            for _, op in ops_until_date.iterrows():
                asset = op['Activo']
                tipo = op['Tipo']
                cantidad = op['Cantidad']
                precio = op['Precio']
                monto = op['Monto']
                
                if asset not in positions:
                    positions[asset] = {'cantidad': 0, 'precio_promedio': 0}
                
                if tipo == 'Compra':
                    # Compra: ingresa monto a la cartera + se compra el activo
                    # Actualizar posición del activo
                    old_qty = positions[asset]['cantidad']
                    old_avg = positions[asset]['precio_promedio']
                    
                    new_qty = old_qty + cantidad
                    if new_qty > 0:
                        new_avg = (old_qty * old_avg + cantidad * precio) / new_qty
                    else:
                        new_avg = precio
                    
                    positions[asset]['cantidad'] = new_qty
                    positions[asset]['precio_promedio'] = new_avg
                    
                    # No afecta cash_flow neto (ingresa monto, sale monto por compra)
                    
                elif tipo == 'Venta':
                    # Venta: sale monto de la cartera + se vende el activo
                    # Reducir posición
                    positions[asset]['cantidad'] -= cantidad
                    # No afecta cash_flow neto (ingresa monto por venta, sale monto de cartera)
                
                elif tipo in ['Cupón', 'Dividendo']:
                    # Cupón/Dividendo: ingresa por cobro, luego sale de la cartera
                    # No afecta cash_flow neto, pero es ganancia realizada
                    pass
                
                elif tipo == 'Flujo':
                    # Flujo de caja directo (aportes/retiros netos)
                    cash_flow += monto
            
            # Calcular valor de la cartera (solo valor de mercado de activos)
            portfolio_value = 0  # Empezar en 0, no incluir cash
            
            for asset, pos in positions.items():
                if pos['cantidad'] > 0:
                    # Obtener precio actual del activo
                    asset_prices = self.precios[
                        (self.precios['Activo'] == asset) & 
                        (self.precios['Fecha'] <= date)
                    ]
                    
                    if not asset_prices.empty:
                        current_price = asset_prices.iloc[-1]['Precio']
                        asset_value = pos['cantidad'] * current_price
                        portfolio_value += asset_value
            
            portfolio_values.append({
                'Fecha': date,
                'Valor_Cartera': portfolio_value,
                'Flujo_Cash': cash_flow
            })
        
        return pd.DataFrame(portfolio_values)
    
    def calculate_daily_returns(self) -> pd.DataFrame:
        """Calcular rendimientos diarios de la cartera"""
        if self.portfolio_data is None:
            self.portfolio_data = self.calculate_portfolio_value()
        
        # Obtener valores de la cartera
        portfolio_data = self.portfolio_data.copy()
        
        # Calcular rendimientos considerando que el valor inicial es la primera compra
        returns = []
        previous_value = None
        
        for i, row in portfolio_data.iterrows():
            current_value = row['Valor_Cartera']
            
            if previous_value is None or previous_value == 0:
                # Primer día o valor anterior cero
                daily_return = 0.0
            else:
                # Calcular rendimiento diario
                daily_return = (current_value - previous_value) / previous_value
            
            returns.append(daily_return)
            previous_value = current_value
        
        # Crear DataFrame
        returns_df = pd.DataFrame({
            'Fecha': portfolio_data['Fecha'],
            'Rendimiento_Diario': returns,
            'Valor_Cartera': portfolio_data['Valor_Cartera']
        })
        
        # Filtrar valores válidos (donde hay activos en cartera)
        returns_df = returns_df[returns_df['Valor_Cartera'] > 0].copy()
        
        self.daily_returns = returns_df
        return returns_df
    
    def calculate_metrics(self, risk_free_rate: float = 0.05) -> Dict:
        """Calcular métricas de performance"""
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        returns = self.daily_returns['Rendimiento_Diario']
        
        # Métricas básicas
        total_return = (1 + returns).prod() - 1
        days = len(returns)
        annualized_return = (1 + total_return) ** (252 / days) - 1
        
        # Volatilidad
        volatility = returns.std() * np.sqrt(252)
        
        # Sharpe ratio
        excess_return = annualized_return - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        
        # Drawdown
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Métricas adicionales
        positive_days = (returns > 0).sum()
        win_rate = positive_days / days
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Sortino ratio (solo desviación negativa)
        negative_returns = returns[returns < 0]
        downside_volatility = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
        sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0
        
        # VaR (Value at Risk) 95%
        var_95 = np.percentile(returns, 5)
        
        # CVaR (Conditional Value at Risk) 95%
        cvar_95 = returns[returns <= var_95].mean()
        
        self.metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'total_days': days,
            'positive_days': positive_days
        }
        
        return self.metrics
    
    def calculate_benchmark_comparison(self, benchmark_returns: pd.Series) -> Dict:
        """Comparar con un benchmark"""
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        portfolio_returns = self.daily_returns['Rendimiento_Diario']
        
        # Alinear fechas
        common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
        portfolio_aligned = portfolio_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # Calcular métricas de comparación
        excess_returns = portfolio_aligned - benchmark_aligned
        
        # Alpha (intercepto de la regresión)
        beta = np.cov(portfolio_aligned, benchmark_aligned)[0, 1] / np.var(benchmark_aligned)
        alpha = portfolio_aligned.mean() - beta * benchmark_aligned.mean()
        
        # Tracking error
        tracking_error = excess_returns.std() * np.sqrt(252)
        
        # Information ratio
        information_ratio = excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0
        
        return {
            'alpha': alpha,
            'beta': beta,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'excess_return': excess_returns.mean()
        }
    
    def calculate_attribution_analysis(self) -> pd.DataFrame:
        """Análisis de atribución por activo"""
        if self.portfolio_data is None:
            self.portfolio_data = self.calculate_portfolio_value()
        
        # Obtener activos únicos
        assets = self.operaciones['Activo'].unique()
        
        attribution_data = []
        
        for asset in assets:
            # Obtener operaciones del activo
            asset_ops = self.operaciones[self.operaciones['Activo'] == asset]
            
            # Calcular posición promedio
            total_invested = 0
            total_quantity = 0
            
            for _, op in asset_ops.iterrows():
                if op['Tipo'] == 'Compra':
                    total_invested += op['Monto']
                    total_quantity += op['Cantidad']
                elif op['Tipo'] == 'Venta':
                    total_invested -= op['Monto']
                    total_quantity -= op['Cantidad']
            
            if total_quantity > 0:
                avg_price = total_invested / total_quantity
                
                # Obtener precio actual (verificar que existan datos)
                asset_prices = self.precios[self.precios['Activo'] == asset]
                if not asset_prices.empty:
                    current_price = asset_prices['Precio'].iloc[-1]
                    first_price = asset_prices['Precio'].iloc[0]
                    
                    # Calcular retorno del activo desde el inicio
                    asset_return = (current_price - avg_price) / avg_price if avg_price > 0 else 0
                    total_return = (current_price - first_price) / first_price if first_price > 0 else 0
                    
                    # Calcular contribución al portfolio
                    current_value = total_quantity * current_price
                    portfolio_value = self.portfolio_data['Valor_Cartera'].iloc[-1] if not self.portfolio_data.empty else 1
                    weight = current_value / portfolio_value if portfolio_value > 0 else 0
                    
                    attribution_data.append({
                        'Activo': asset,
                        'Peso': weight,
                        'Retorno_vs_Costo': asset_return,
                        'Retorno_Total': total_return,
                        'Contribucion': weight * asset_return,
                        'Valor_Actual': current_value,
                        'Precio_Promedio': avg_price,
                        'Precio_Actual': current_price,
                        'Precio_Inicial': first_price,
                        'Cantidad': total_quantity,
                        'Inversion_Total': total_invested
                    })
        
        return pd.DataFrame(attribution_data)
    
    def calculate_individual_asset_performance(self) -> pd.DataFrame:
        """Calcular rendimiento individual de cada activo a lo largo del tiempo"""
        # Obtener activos únicos
        assets = self.operaciones['Activo'].unique()
        
        # Crear DataFrame con fechas únicas
        dates = self.precios['Fecha'].unique()
        dates = sorted(dates)
        
        performance_data = []
        
        for asset in assets:
            # Obtener precios del activo
            asset_prices = self.precios[self.precios['Activo'] == asset].copy()
            asset_prices = asset_prices.sort_values('Fecha')
            
            if not asset_prices.empty:
                # Calcular rendimientos diarios
                asset_prices['Rendimiento_Diario'] = asset_prices['Precio'].pct_change()
                asset_prices['Rendimiento_Acumulado'] = (1 + asset_prices['Rendimiento_Diario']).cumprod() - 1
                
                # Agregar información del activo
                for _, row in asset_prices.iterrows():
                    performance_data.append({
                        'Fecha': row['Fecha'],
                        'Activo': asset,
                        'Precio': row['Precio'],
                        'Rendimiento_Diario': row['Rendimiento_Diario'],
                        'Rendimiento_Acumulado': row['Rendimiento_Acumulado']
                    })
        
        return pd.DataFrame(performance_data)
    
    def get_asset_summary_stats(self) -> pd.DataFrame:
        """Obtener estadísticas resumidas de cada activo"""
        individual_performance = self.calculate_individual_asset_performance()
        
        if individual_performance.empty:
            return pd.DataFrame()
        
        summary_stats = []
        
        for asset in individual_performance['Activo'].unique():
            asset_data = individual_performance[individual_performance['Activo'] == asset]
            
            if not asset_data.empty:
                returns = asset_data['Rendimiento_Diario'].dropna()
                
                if len(returns) > 0:
                    summary_stats.append({
                        'Activo': asset,
                        'Rendimiento_Total': asset_data['Rendimiento_Acumulado'].iloc[-1],
                        'Rendimiento_Anualizado': (1 + asset_data['Rendimiento_Acumulado'].iloc[-1]) ** (252 / len(asset_data)) - 1,
                        'Volatilidad_Anualizada': returns.std() * np.sqrt(252),
                        'Sharpe_Ratio': (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0,
                        'Rendimiento_Maximo': returns.max(),
                        'Rendimiento_Minimo': returns.min(),
                        'Dias_Positivos': (returns > 0).sum(),
                        'Dias_Negativos': (returns < 0).sum(),
                        'Precio_Inicial': asset_data['Precio'].iloc[0],
                        'Precio_Final': asset_data['Precio'].iloc[-1],
                        'Precio_Maximo': asset_data['Precio'].max(),
                        'Precio_Minimo': asset_data['Precio'].min()
                    })
        
        return pd.DataFrame(summary_stats)
    
    def get_performance_summary(self) -> pd.DataFrame:
        """Resumen de performance por período"""
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        # Crear columna de año-mes como string para evitar problemas con Period
        self.daily_returns['Año_Mes'] = self.daily_returns['Fecha'].dt.strftime('%Y-%m')
        
        # Agrupar por mes
        monthly_returns = self.daily_returns.groupby('Año_Mes')['Rendimiento_Diario'].apply(
            lambda x: (1 + x).prod() - 1
        )
        
        # Calcular métricas mensuales
        monthly_volatility = self.daily_returns.groupby('Año_Mes')['Rendimiento_Diario'].std() * np.sqrt(252)
        
        monthly_metrics = pd.DataFrame({
            'Retorno_Mensual': monthly_returns,
            'Volatilidad_Mensual': monthly_volatility,
            'Sharpe_Mensual': monthly_returns / monthly_volatility
        })
        
        # Convertir el índice a datetime para mejor visualización
        monthly_metrics.index = pd.to_datetime(monthly_metrics.index + '-01')
        monthly_metrics.index.name = 'Fecha'
        
        return monthly_metrics
