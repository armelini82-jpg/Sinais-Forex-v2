"""
IQS - Intelligent Quality Score.

Motor de decisão que NÃO se limita a indicadores isolados: combina tendência,
momentum, pullback, volatilidade, força de tendência (ADX), liquidez/spread e
sessão de mercado em um score único de 0 a 100, com os pesos definidos no
briefing do produto:

    Trend        25
    Momentum     15
    Pullback     20
    Volatilidade 15
    ADX          10
    Liquidez     10
    Sessão        5
    -----------------
    Total       100

Regras de negócio:
    IQS >= 90                -> sinal CONFIRMADO
    80 <= IQS < 90            -> sinal PREPARANDO
    IQS < 80                  -> DESCARTADO
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Literal

from app.core.config import settings
from app.schemas.candle import CandleDTO
from app.schemas.indicator import IndicatorSetDTO
from app.schemas.signal import IQSBreakdownDTO

Direction = Literal["BUY", "SELL", "NEUTRAL"]

# Pesos oficiais do IQS
WEIGHT_TREND = 25
WEIGHT_MOMENTUM = 15
WEIGHT_PULLBACK = 20
WEIGHT_VOLATILITY = 15
WEIGHT_ADX = 10
WEIGHT_LIQUIDITY = 10
WEIGHT_SESSION = 5


@dataclass
class IQSResult:
    direction: Direction
    breakdown: IQSBreakdownDTO
    total_score: float
    status: str  # CONFIRMADO | PREPARANDO | DESCARTADO


class IQSEngine:
    """Calcula o IQS e a direção sugerida (BUY/SELL) para um símbolo/timeframe."""

    def evaluate(
        self,
        symbol: str,
        candles: List[CandleDTO],
        indicators: IndicatorSetDTO,
    ) -> IQSResult:
        direction = self._infer_direction(indicators)

        trend_score = self._score_trend(indicators, direction)
        momentum_score = self._score_momentum(indicators, direction)
        pullback_score = self._score_pullback(candles, indicators, direction)
        volatility_score = self._score_volatility(candles, indicators)
        adx_score = self._score_adx(indicators)
        liquidity_score = self._score_liquidity(candles, symbol)
        session_score = self._score_session(symbol)

        breakdown = IQSBreakdownDTO(
            trend=trend_score,
            momentum=momentum_score,
            pullback=pullback_score,
            volatility=volatility_score,
            adx=adx_score,
            liquidity=liquidity_score,
            session=session_score,
        )

        total = breakdown.total
        status = self._classify(total)

        return IQSResult(direction=direction, breakdown=breakdown, total_score=total, status=status)

    # ------------------------------------------------------------------
    # Sub-scores
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_direction(ind: IndicatorSetDTO) -> Direction:
        """Direção baseada no alinhamento das EMAs (estrutura de tendência)."""
        if ind.ema_9 and ind.ema_21 and ind.ema_200:
            if ind.ema_9 > ind.ema_21 > ind.ema_200:
                return "BUY"
            if ind.ema_9 < ind.ema_21 < ind.ema_200:
                return "SELL"
        return "NEUTRAL"

    @staticmethod
    def _score_trend(ind: IndicatorSetDTO, direction: Direction) -> float:
        """Tendência: alinhamento de EMAs + inclinação do MACD."""
        if direction == "NEUTRAL" or not (ind.ema_9 and ind.ema_21 and ind.ema_200):
            return 0.0

        spread_9_21 = abs(ind.ema_9 - ind.ema_21) / ind.ema_21
        spread_21_200 = abs(ind.ema_21 - ind.ema_200) / ind.ema_200
        alignment_strength = min(1.0, (spread_9_21 + spread_21_200) * 200)

        macd_ok = (
            (ind.macd_hist is not None and ind.macd_hist > 0 and direction == "BUY")
            or (ind.macd_hist is not None and ind.macd_hist < 0 and direction == "SELL")
        )
        macd_component = 1.0 if macd_ok else 0.4

        score = WEIGHT_TREND * (0.7 * alignment_strength + 0.3 * macd_component)
        return round(min(score, WEIGHT_TREND), 2)

    @staticmethod
    def _score_momentum(ind: IndicatorSetDTO, direction: Direction) -> float:
        """Momentum: RSI fora da zona neutra na direção certa + momentum bruto."""
        if direction == "NEUTRAL" or ind.rsi_14 is None or ind.momentum is None:
            return 0.0

        if direction == "BUY":
            rsi_component = max(0.0, min(1.0, (ind.rsi_14 - 50) / 30))
            momentum_component = max(0.0, min(1.0, ind.momentum / 0.5))
        else:
            rsi_component = max(0.0, min(1.0, (50 - ind.rsi_14) / 30))
            momentum_component = max(0.0, min(1.0, -ind.momentum / 0.5))

        score = WEIGHT_MOMENTUM * (0.6 * rsi_component + 0.4 * momentum_component)
        return round(min(score, WEIGHT_MOMENTUM), 2)

    @staticmethod
    def _score_pullback(candles: List[CandleDTO], ind: IndicatorSetDTO, direction: Direction) -> float:
        """
        Pullback: identifica se o preço recuou até a EMA 21 (zona de valor) e
        está retomando a direção da tendência - entrada de melhor risco/retorno
        do que perseguir o preço no rompimento.
        """
        if direction == "NEUTRAL" or ind.ema_21 is None or not candles:
            return 0.0

        last_close = candles[-1].close
        distance_to_ema21 = abs(last_close - ind.ema_21) / ind.ema_21

        # Quanto mais perto da EMA21 (mas sem cruzar contra a tendência), melhor.
        proximity_component = max(0.0, 1.0 - min(1.0, distance_to_ema21 * 300))

        recent = candles[-3:]
        if direction == "BUY":
            resuming = recent[-1].close > recent[0].close
        else:
            resuming = recent[-1].close < recent[0].close
        resume_component = 1.0 if resuming else 0.5

        score = WEIGHT_PULLBACK * (0.6 * proximity_component + 0.4 * resume_component)
        return round(min(score, WEIGHT_PULLBACK), 2)

    @staticmethod
    def _score_volatility(candles: List[CandleDTO], ind: IndicatorSetDTO) -> float:
        """
        Volatilidade: ATR saudável em relação ao preço (nem mercado morto, nem
        volatilidade explosiva incontrolável).
        """
        if ind.atr_14 is None or not candles:
            return 0.0

        last_close = candles[-1].close
        atr_ratio = ind.atr_14 / last_close if last_close else 0.0

        # Faixa ideal de ATR relativo: 0.03% a 0.35% do preço (calibrado para forex intraday)
        if 0.0003 <= atr_ratio <= 0.0035:
            component = 1.0
        elif atr_ratio < 0.0003:
            component = max(0.0, atr_ratio / 0.0003)
        else:
            component = max(0.0, 1.0 - (atr_ratio - 0.0035) / 0.01)

        score = WEIGHT_VOLATILITY * component
        return round(min(score, WEIGHT_VOLATILITY), 2)

    @staticmethod
    def _score_adx(ind: IndicatorSetDTO) -> float:
        """ADX: força da tendência. Abaixo de 20 = mercado lateral (descarta força)."""
        if ind.adx_14 is None:
            return 0.0
        component = max(0.0, min(1.0, (ind.adx_14 - 15) / 30))
        score = WEIGHT_ADX * component
        return round(min(score, WEIGHT_ADX), 2)

    @staticmethod
    def _score_liquidity(candles: List[CandleDTO], symbol: str) -> float:
        """
        Liquidez/spread: proxy via volume relativo recente e amplitude do
        candle atual vs. média (spreads maiores tendem a coincidir com
        candles anormalmente largos e volume errático).
        """
        if not candles or len(candles) < 20:
            return 0.0

        volumes = [c.volume for c in candles[-20:]]
        avg_volume = sum(volumes) / len(volumes)
        last_volume = candles[-1].volume
        volume_ratio = last_volume / avg_volume if avg_volume else 0.0
        volume_component = max(0.0, min(1.0, volume_ratio))

        ranges = [(c.high - c.low) for c in candles[-20:]]
        avg_range = sum(ranges) / len(ranges)
        last_range = candles[-1].high - candles[-1].low
        range_ratio = last_range / avg_range if avg_range else 1.0
        range_component = 1.0 if 0.5 <= range_ratio <= 2.0 else 0.4

        score = WEIGHT_LIQUIDITY * (0.5 * volume_component + 0.5 * range_component)
        return round(min(score, WEIGHT_LIQUIDITY), 2)

    @staticmethod
    def _score_session(symbol: str) -> float:
        """
        Sessão: dá preferência aos horários de maior liquidez para cada grupo
        de pares (overlap Londres/Nova York para majors, sessão de Tóquio
        para pares com JPY).
        """
        hour_utc = datetime.now(timezone.utc).hour

        jpy_pair = "JPY" in symbol
        if jpy_pair:
            good_hours = set(range(0, 9)) | set(range(12, 16))
        else:
            good_hours = set(range(7, 17))

        component = 1.0 if hour_utc in good_hours else 0.4
        score = WEIGHT_SESSION * component
        return round(min(score, WEIGHT_SESSION), 2)

    @staticmethod
    def _classify(total_score: float) -> str:
        if total_score >= settings.IQS_MIN_SIGNAL:
            return "CONFIRMADO"
        if total_score >= settings.IQS_MIN_PREPARING:
            return "PREPARANDO"
        return "DESCARTADO"

    @staticmethod
    def explain(direction: Direction, breakdown: IQSBreakdownDTO) -> str:
        """
        Gera uma explicação curta e legível do motivo pelo qual o par não
        qualificou (ou qualificou parcialmente), com base no componente mais
        fraco do IQS em relação ao seu peso máximo.
        """
        if direction == "NEUTRAL":
            return "Sem alinhamento de tendência (EMAs 9/21/200 não convergem)"

        components = [
            ("Trend", breakdown.trend, WEIGHT_TREND, "tendência fraca ou EMAs desalinhadas"),
            ("Pullback", breakdown.pullback, WEIGHT_PULLBACK, "sem recuo limpo até zona de valor"),
            ("Momentum", breakdown.momentum, WEIGHT_MOMENTUM, "RSI/momentum sem força na direção"),
            ("Volatilidade", breakdown.volatility, WEIGHT_VOLATILITY, "ATR fora da faixa saudável"),
            ("ADX", breakdown.adx, WEIGHT_ADX, "ADX baixo — mercado lateral"),
            ("Liquidez", breakdown.liquidity, WEIGHT_LIQUIDITY, "volume/amplitude atípicos"),
            ("Sessão", breakdown.session, WEIGHT_SESSION, "fora do horário de maior liquidez"),
        ]

        weakest = min(components, key=lambda c: (c[1] / c[2]) if c[2] else 0)
        _, score, weight, phrase = weakest
        return f"{phrase} ({score:.0f}/{weight})"
