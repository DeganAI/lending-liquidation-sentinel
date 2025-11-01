"""
Price Feed System

Fetches token prices from Chainlink oracles, protocol oracles, and CoinGecko fallback
"""
import httpx
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# CoinGecko token mappings
COINGECKO_IDS = {
    "ETH": "ethereum",
    "WETH": "ethereum",
    "MATIC": "matic-network",
    "WMATIC": "matic-network",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "WBTC": "wrapped-bitcoin",
    "LINK": "chainlink",
    "AAVE": "aave",
    "CRV": "curve-dao-token",
    "UNI": "uniswap",
    "SUSHI": "sushi",
    "AVAX": "avalanche-2",
    "WAVAX": "avalanche-2",
    "BNB": "binancecoin",
    "WBNB": "binancecoin",
}


async def get_token_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Get token prices from CoinGecko

    Args:
        symbols: List of token symbols (e.g., ["ETH", "USDC", "DAI"])

    Returns:
        Dictionary mapping symbol to price in USD
    """
    prices = {}

    # Map symbols to CoinGecko IDs
    coingecko_ids = []
    symbol_to_id = {}

    for symbol in symbols:
        cg_id = COINGECKO_IDS.get(symbol.upper())
        if cg_id:
            coingecko_ids.append(cg_id)
            symbol_to_id[cg_id] = symbol.upper()
        else:
            logger.warning(f"No CoinGecko ID mapping for {symbol}")

    if not coingecko_ids:
        logger.error("No valid CoinGecko IDs to fetch")
        return prices

    try:
        # CoinGecko API
        ids_param = ",".join(coingecko_ids)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # Parse response
            for cg_id, price_data in data.items():
                if "usd" in price_data:
                    symbol = symbol_to_id[cg_id]
                    prices[symbol] = price_data["usd"]
                    logger.debug(f"Price for {symbol}: ${price_data['usd']}")

        logger.info(f"Fetched {len(prices)} token prices from CoinGecko")
        return prices

    except httpx.HTTPStatusError as e:
        logger.error(f"CoinGecko API error: {e.response.status_code} - {e.response.text}")
        return prices
    except Exception as e:
        logger.error(f"Error fetching token prices: {e}")
        return prices


async def get_price_from_chainlink(
    token_address: str,
    chain_id: int,
    rpc_url: str
) -> Optional[float]:
    """
    Get token price from Chainlink price feed

    Args:
        token_address: Token contract address
        chain_id: Chain ID
        rpc_url: RPC endpoint URL

    Returns:
        Token price in USD or None
    """
    # This is a placeholder - would need actual Chainlink feed addresses
    # and proper Web3 integration
    logger.warning("Chainlink price feed not yet implemented - using CoinGecko fallback")
    return None


async def get_price_from_protocol(
    token_address: str,
    protocol_oracle_address: str,
    rpc_url: str
) -> Optional[float]:
    """
    Get token price from protocol's oracle

    Args:
        token_address: Token contract address
        protocol_oracle_address: Protocol oracle contract address
        rpc_url: RPC endpoint URL

    Returns:
        Token price in USD or None
    """
    # This is a placeholder - would need protocol-specific oracle interfaces
    logger.warning("Protocol oracle not yet implemented - using CoinGecko fallback")
    return None


async def get_token_price_with_fallback(
    symbol: str,
    token_address: Optional[str] = None,
    chain_id: Optional[int] = None,
    rpc_url: Optional[str] = None
) -> Optional[float]:
    """
    Get token price with fallback strategy:
    1. Try Chainlink oracle
    2. Try protocol oracle
    3. Fall back to CoinGecko

    Args:
        symbol: Token symbol
        token_address: Token contract address (optional)
        chain_id: Chain ID (optional)
        rpc_url: RPC endpoint (optional)

    Returns:
        Token price in USD or None
    """
    # Try Chainlink first (if we have token address)
    if token_address and chain_id and rpc_url:
        chainlink_price = await get_price_from_chainlink(token_address, chain_id, rpc_url)
        if chainlink_price:
            logger.info(f"Got {symbol} price from Chainlink: ${chainlink_price}")
            return chainlink_price

    # Fall back to CoinGecko
    prices = await get_token_prices([symbol])
    if symbol.upper() in prices:
        price = prices[symbol.upper()]
        logger.info(f"Got {symbol} price from CoinGecko: ${price}")
        return price

    logger.error(f"Failed to get price for {symbol}")
    return None
