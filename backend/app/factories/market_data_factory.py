"""
Factory responsável por instanciar o provedor de dados de mercado correto
de acordo com `settings.DATA_PROVIDER`. Novos provedores reais (OANDA, MT5)
devem ser registrados aqui, sem alterar os services consumidores.
"""
from app.core.config import settings
from app.interfaces.market_data_interface import IMarketDataProvider
from app.services.market_data_service import simulated_market_data_provider
from app.services.twelvedata_provider import TwelveDataMarketDataProvider

_twelvedata_instance: IMarketDataProvider | None = None


class MarketDataProviderFactory:
    @staticmethod
    def create() -> IMarketDataProvider:
        provider = settings.DATA_PROVIDER.lower()

        if provider == "simulated":
            return simulated_market_data_provider

        if provider == "twelvedata":
            global _twelvedata_instance
            if _twelvedata_instance is None:
                # Instância única: preserva o cache e o rate limiter internos
                # entre as chamadas do scheduler e dos endpoints da API.
                _twelvedata_instance = TwelveDataMarketDataProvider(
                    api_key=settings.MARKET_DATA_API_KEY
                )
            return _twelvedata_instance

        # Pontos de extensão para produção:
        # if provider == "oanda":
        #     return OandaMarketDataProvider(api_key=settings.MARKET_DATA_API_KEY)
        # if provider == "mt5":
        #     return MT5MarketDataProvider()

        raise ValueError(
            f"DATA_PROVIDER '{provider}' não implementado. "
            "Use 'simulated', 'twelvedata' ou implemente um novo provider em "
            "services/ e registre-o nesta factory."
        )
