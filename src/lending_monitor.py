"""
Lending Position Monitor

Core logic for health factor calculation and liquidation price estimation
"""
import os
import logging
from typing import Dict, List, Optional
from src.protocol_interfaces import (
    ProtocolType,
    get_protocol_interface,
    CHAIN_NAMES
)
from src.price_feed import get_token_prices

logger = logging.getLogger(__name__)


class LendingMonitor:
    """Monitor lending positions across protocols"""

    # Default RPC URLs (can be overridden with env vars)
    DEFAULT_RPC_URLS = {
        1: "https://eth.llamarpc.com",
        137: "https://polygon.llamarpc.com",
        42161: "https://arbitrum.llamarpc.com",
        10: "https://optimism.llamarpc.com",
        8453: "https://base.llamarpc.com",
        43114: "https://avalanche.llamarpc.com",
        56: "https://binance.llamarpc.com"
    }

    def __init__(self):
        """Initialize lending monitor"""
        self.rpc_urls = {}

        # Load RPC URLs from environment or use defaults
        for chain_id in self.DEFAULT_RPC_URLS.keys():
            env_key = f"CHAIN_{chain_id}_RPC_URL"
            self.rpc_urls[chain_id] = os.getenv(env_key, self.DEFAULT_RPC_URLS[chain_id])

        logger.info(f"Lending monitor initialized with {len(self.rpc_urls)} chains")

    async def monitor_position(
        self,
        wallet: str,
        protocol: ProtocolType,
        chain_id: int,
        position_filters: Optional[List] = None
    ) -> Optional[Dict]:
        """
        Monitor a lending position

        Args:
            wallet: Wallet address to monitor
            protocol: Protocol type
            chain_id: Chain ID
            position_filters: Optional filters for specific positions

        Returns:
            Position data including health factor and liquidation price
        """
        try:
            # Get RPC URL
            if chain_id not in self.rpc_urls:
                logger.error(f"Chain {chain_id} not supported")
                return None

            rpc_url = self.rpc_urls[chain_id]

            # Get protocol interface
            protocol_interface = get_protocol_interface(protocol, chain_id, rpc_url)

            # Fetch account data
            account_data = await protocol_interface.get_user_account_data(wallet)

            if not account_data:
                logger.error(f"Failed to fetch account data for {wallet}")
                return None

            # Calculate liquidation price (simplified - for primary collateral)
            liq_price = None
            if account_data["total_debt_usd"] > 0 and account_data["total_collateral_usd"] > 0:
                # Simplified calculation: liq_price = debt / (collateral * liq_threshold)
                # This assumes single asset collateral for simplicity
                liquidation_threshold = account_data["liquidation_threshold"]
                liq_price = account_data["total_debt_usd"] / (
                    account_data["total_collateral_usd"] * liquidation_threshold
                )

            # Get chain name
            chain_name = CHAIN_NAMES.get(chain_id, f"Chain {chain_id}")

            return {
                "chain_name": chain_name,
                "health_factor": account_data["health_factor"],
                "liq_price": liq_price,
                "total_collateral_usd": account_data["total_collateral_usd"],
                "total_debt_usd": account_data["total_debt_usd"],
                "liquidation_threshold": account_data["liquidation_threshold"],
                "ltv": account_data["ltv"],
                "positions": account_data.get("positions", [])
            }

        except Exception as e:
            logger.error(f"Error monitoring position: {e}", exc_info=True)
            return None

    def calculate_health_factor(
        self,
        total_collateral_usd: float,
        total_debt_usd: float,
        liquidation_threshold: float
    ) -> float:
        """
        Calculate health factor

        Formula: HF = (total_collateral * liquidation_threshold) / total_debt

        Args:
            total_collateral_usd: Total collateral in USD
            total_debt_usd: Total debt in USD
            liquidation_threshold: Liquidation threshold (e.g., 0.825 for 82.5%)

        Returns:
            Health factor (< 1.0 = liquidatable)
        """
        if total_debt_usd == 0:
            return float('inf')

        return (total_collateral_usd * liquidation_threshold) / total_debt_usd

    def calculate_liquidation_price(
        self,
        collateral_amount: float,
        debt_amount: float,
        debt_price: float,
        liquidation_threshold: float,
        liquidation_bonus: float = 1.05
    ) -> float:
        """
        Calculate liquidation price for single-asset collateral

        Formula: liq_price = (debt * debt_price) / (collateral * liq_threshold)

        Args:
            collateral_amount: Amount of collateral
            debt_amount: Amount of debt
            debt_price: Price of debt asset
            liquidation_threshold: Liquidation threshold
            liquidation_bonus: Liquidation bonus (e.g., 1.05 = 5% bonus)

        Returns:
            Liquidation price for collateral asset
        """
        if collateral_amount == 0:
            return 0

        # Account for liquidation bonus
        effective_threshold = liquidation_threshold / liquidation_bonus

        return (debt_amount * debt_price) / (collateral_amount * effective_threshold)

    def should_alert(self, health_factor: float, threshold: float = 1.2) -> tuple:
        """
        Determine if alert should be triggered

        Args:
            health_factor: Current health factor
            threshold: Alert threshold (default 1.2 = 20% buffer)

        Returns:
            Tuple of (should_alert: bool, severity: str)
        """
        if health_factor < 1.05:
            return True, "critical"
        elif health_factor < threshold:
            return True, "warning"
        else:
            return False, "safe"
