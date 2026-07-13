"""
Motor de cálculo de indicadores técnicos.

Utiliza a biblioteca `ta` (pandas-based, pura Python, sem dependências
binárias) para calcular EMA 9/21/200, RSI 14, ATR 14, ADX, MACD, Bandas de
Bollinger, VWAP e Momentum a partir de uma série de candles.
"""
from typing import List

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import VolumeWeightedAveragePrice

from app.core.exceptions import InsufficientDataError
from app.schemas.candle import CandleDTO
from app.schemas.indicator import IndicatorSetDTO

MIN_CANDLES_REQUIRED = 210  # cobre a EMA 200 com folga


class IndicatorService:
    """Calcula o conjunto completo de indicadores técnicos para um símbolo/timeframe."""

    def calculate(self, symbol: str, timeframe: str, candles: List[CandleDTO]) -> IndicatorSetDTO:
        if len(candles) < MIN_CANDLES_REQUIRED:
            raise InsufficientDataError(symbol, timeframe)

        df = self._to_dataframe(candles)

        ema_9 = EMAIndicator(close=df["close"], window=9).ema_indicator()
        ema_21 = EMAIndicator(close=df["close"], window=21).ema_indicator()
        ema_200 = EMAIndicator(close=df["close"], window=200).ema_indicator()

        rsi_14 = RSIIndicator(close=df["close"], window=14).rsi()

        atr_14 = AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"], window=14
        ).average_true_range()

        adx_indicator = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
        adx_14 = adx_indicator.adx()

        macd_indicator = MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd_indicator.macd()
        macd_signal = macd_indicator.macd_signal()
        macd_hist = macd_indicator.macd_diff()

        bollinger = BollingerBands(close=df["close"], window=20, window_dev=2)
        bb_upper = bollinger.bollinger_hband()
        bb_middle = bollinger.bollinger_mavg()
        bb_lower = bollinger.bollinger_lband()

        vwap = VolumeWeightedAveragePrice(
            high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], window=14
        ).volume_weighted_average_price()

        # Momentum simples: variação percentual dos últimos 10 períodos
        momentum = df["close"].pct_change(periods=10) * 100

        return IndicatorSetDTO(
            ema_9=self._last(ema_9),
            ema_21=self._last(ema_21),
            ema_200=self._last(ema_200),
            rsi_14=self._last(rsi_14),
            atr_14=self._last(atr_14),
            adx_14=self._last(adx_14),
            macd=self._last(macd_line),
            macd_signal=self._last(macd_signal),
            macd_hist=self._last(macd_hist),
            bb_upper=self._last(bb_upper),
            bb_middle=self._last(bb_middle),
            bb_lower=self._last(bb_lower),
            vwap=self._last(vwap),
            momentum=self._last(momentum),
            volume=float(df["volume"].iloc[-1]),
        )

    @staticmethod
    def _to_dataframe(candles: List[CandleDTO]) -> pd.DataFrame:
        data = {
            "open_time": [c.open_time for c in candles],
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
        df = pd.DataFrame(data).sort_values("open_time").reset_index(drop=True)
        return df

    @staticmethod
    def _last(series: pd.Series) -> float:
        value = series.iloc[-1]
        if pd.isna(value):
            return 0.0
        return round(float(value), 6)
