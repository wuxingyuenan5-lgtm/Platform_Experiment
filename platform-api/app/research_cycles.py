"""Read-only inputs for descriptive market cycles, with native provenance intact."""

from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError
from app.research_seasonality import read_seasonality

MACRO_INPUTS = {
    "usGrowth": "us_indpro_yoy",
    "usInflation": "us_cpi_yoy",
    "cnGrowth": "cn_industrial_yoy",
    "cnInflation": "cn_cpi_yoy",
    "policy": "fed_target_upper",
    "realYield": "us_10y_real_yield",
    "dollar": "dxy",
    "liquidity": "net_dollar_liquidity",
    "cnCredit": "cn_tsf_stock_yoy",
    "cnProfit": "cn_industrial_profit_ytd_yoy",
}


def _local(path):
    try:
        return read_local_json(path)
    except ResearchProviderError as exc:
        return {"status": "error", "isStale": True, "observations": [], "errorCode": str(exc)}


def read_cycles():
    indicators = {
        key: _local(f"public/v1/macro/series/{name}.json")
        for key, name in MACRO_INPUTS.items()
    }
    assets = {}
    for key in ["us-spy", "us-gld", "cn-hs300"]:
        try:
            assets[key] = read_seasonality(key)
        except ResearchProviderError as exc:
            assets[key] = {"status": "error", "isStale": True, "observations": [], "errorCode": str(exc)}
    assets["btc-usd"] = _local("public/v1/crypto/series/btc_blockchain_market_price.json")
    return {"indicators": indicators, "assets": assets, "methodologyVersion": "descriptive-cycles-v1"}
