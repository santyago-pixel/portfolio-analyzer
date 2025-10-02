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
        self.precios['Fecha'] = pd.to_datetime(self.precios['Fecha'])
        
        # Ordenar por fecha
        self.operaciones = self.operaciones.sort_values('Fecha')
        self.precios = self.precios.sort_values('Fecha')
        
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
                
                if tipo in ['Compra', 'Cupón', 'Dividendo']:
                    if tipo == 'Compra':
                        # Actualizar posición
                        old_qty = positions[asset]['cantidad']
                        old_avg = positions[asset]['precio_promedio']
                        
                        new_qty = old_qty + cantidad
                        if new_qty > 0:
                            new_avg = (old_qty * old_avg + cantidad * precio) / new_qty
                        else:
                            new_avg = precio
                        
                        positions[asset]['cantidad'] = new_qty
                        positions[asset]['precio_promedio'] = new_avg
                    else:
                        # Cupón o dividendo - flujo de caja
                        cash_flow += monto
                
                elif tipo == 'Venta':
                    # Reducir posición
                    positions[asset]['cantidad'] -= cantidad
                    cash_flow += monto
                
                elif tipo == 'Flujo':
                    # Flujo de caja directo
                    cash_flow += monto
            
            # Calcular valor de la cartera
            portfolio_value = cash_flow
            
            for asset, pos in positions.items():
                if pos['cantidad'] > 0:
                    # Obtener precio actual del activo
                    asset_prices = self.precios[
                        (self.precios['Activo'] == asset) & 
                        (self.precios['Fecha'] <= date)
                    ]
                    
                    if not asset_prices.empty:
                        current_price = asset_prices.iloc[-1]['Precio']
                        portfolio_value += pos['cantidad'] * current_price
            
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
        
        # Calcular rendimientos diarios
        portfolio_values = self.portfolio_data['Valor_Cartera'].values
        
        # Calcular rendimientos
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        returns = np.insert(returns, 0, 0)  # Primer día = 0
        
        # Crear DataFrame
        returns_df = pd.DataFrame({
            'Fecha': self.portfolio_data['Fecha'],
            'Rendimiento_Diario': returns,
            'Valor_Cartera': portfolio_values
        })
        
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
                
                # Obtener precio actual
                current_price = self.precios[
                    self.precios['Activo'] == asset
                ]['Precio'].iloc[-1]
                
                # Calcular retorno del activo
                asset_return = (current_price - avg_price) / avg_price
                
                # Calcular contribución al portfolio
                current_value = total_quantity * current_price
                portfolio_value = self.portfolio_data['Valor_Cartera'].iloc[-1]
                weight = current_value / portfolio_value if portfolio_value > 0 else 0
                
                attribution_data.append({
                    'Activo': asset,
                    'Peso': weight,
                    'Retorno': asset_return,
                    'Contribucion': weight * asset_return,
                    'Valor_Actual': current_value,
                    'Cantidad': total_quantity
                })
        
        return pd.DataFrame(attribution_data)
    
    def get_performance_summary(self) -> pd.DataFrame:
        """Resumen de performance por período"""
        if self.daily_returns is None:
            self.calculate_daily_returns()
        
        # Agrupar por mes
        monthly_returns = self.daily_returns.groupby(
            self.daily_returns['Fecha'].dt.to_period('M')
        )['Rendimiento_Diario'].apply(lambda x: (1 + x).prod() - 1)
        
        # Calcular métricas mensuales
        monthly_metrics = pd.DataFrame({
            'Retorno_Mensual': monthly_returns,
            'Volatilidad_Mensual': self.daily_returns.groupby(
                self.daily_returns['Fecha'].dt.to_period('M')
            )['Rendimiento_Diario'].std() * np.sqrt(252),
            'Sharpe_Mensual': monthly_returns / (
                self.daily_returns.groupby(
                    self.daily_returns['Fecha'].dt.to_period('M')
                )['Rendimiento_Diario'].std() * np.sqrt(252)
            )
        })
        
        return monthly_metrics
