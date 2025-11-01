"""
Protocol Interfaces for Lending Platforms

Interfaces for Aave V3, Compound V3, Spark, and Radiant
"""
from enum import Enum
from typing import Dict, List, Optional
from web3 import Web3
import logging

logger = logging.getLogger(__name__)


class ProtocolType(str, Enum):
    """Supported lending protocols"""
    AAVE_V3 = "aave_v3"
    COMPOUND_V3 = "compound_v3"
    SPARK = "spark"
    RADIANT = "radiant"


# Chain configurations
CHAIN_NAMES = {
    1: "Ethereum",
    137: "Polygon",
    42161: "Arbitrum",
    10: "Optimism",
    8453: "Base",
    43114: "Avalanche",
    56: "BSC"
}

# Protocol addresses by chain
AAVE_V3_POOL_ADDRESSES = {
    1: "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",  # Ethereum
    137: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # Polygon
    42161: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # Arbitrum
    10: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # Optimism
    8453: "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",  # Base
    43114: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # Avalanche
}

COMPOUND_V3_COMET_ADDRESSES = {
    1: "0xc3d688B66703497DAA19211EEdff47f25384cdc3",  # Ethereum USDC
    137: "0xF25212E676D1F7F89Cd72fFEe66158f541246445",  # Polygon USDC
    42161: "0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA",  # Arbitrum USDC
    8453: "0xb125E6687d4313864e53df431d5425969c15Eb2F",  # Base USDC
}

SPARK_POOL_ADDRESSES = {
    1: "0xC13e21B648A5Ee794902342038FF3aDAB66BE987",  # Ethereum
}

RADIANT_POOL_ADDRESSES = {
    42161: "0xF4B1486DD74D07706052A33d31d7c0AAFD0659E1",  # Arbitrum
    43114: "0xF4B1486DD74D07706052A33d31d7c0AAFD0659E1",  # Avalanche
    56: "0xd50Cf00b6e600Dd036Ba8eF475677d816d6c4281",  # BSC
}

# Aave V3 Pool ABI (minimal)
AAVE_V3_POOL_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"internalType": "uint256", "name": "totalCollateralBase", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDebtBase", "type": "uint256"},
            {"internalType": "uint256", "name": "availableBorrowsBase", "type": "uint256"},
            {"internalType": "uint256", "name": "currentLiquidationThreshold", "type": "uint256"},
            {"internalType": "uint256", "name": "ltv", "type": "uint256"},
            {"internalType": "uint256", "name": "healthFactor", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getUserConfiguration",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Compound V3 Comet ABI (minimal)
COMPOUND_V3_COMET_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "borrowBalanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "collateralBalanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getPrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class ProtocolInterface:
    """Base protocol interface"""

    def __init__(self, chain_id: int, rpc_url: str):
        self.chain_id = chain_id
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC for chain {chain_id}")

    async def get_user_account_data(self, wallet: str) -> Optional[Dict]:
        """Get user account data - must be implemented by subclass"""
        raise NotImplementedError


class AaveV3Interface(ProtocolInterface):
    """Aave V3 Protocol Interface"""

    def __init__(self, chain_id: int, rpc_url: str):
        super().__init__(chain_id, rpc_url)

        if chain_id not in AAVE_V3_POOL_ADDRESSES:
            raise ValueError(f"Aave V3 not supported on chain {chain_id}")

        pool_address = AAVE_V3_POOL_ADDRESSES[chain_id]
        self.pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=AAVE_V3_POOL_ABI
        )

    async def get_user_account_data(self, wallet: str) -> Optional[Dict]:
        """Get Aave V3 user account data"""
        try:
            wallet_checksum = Web3.to_checksum_address(wallet)

            # Call getUserAccountData
            (
                total_collateral_base,
                total_debt_base,
                available_borrows_base,
                current_liquidation_threshold,
                ltv,
                health_factor
            ) = self.pool_contract.functions.getUserAccountData(wallet_checksum).call()

            # Convert from base units (8 decimals for values, 4 for percentages)
            return {
                "total_collateral_usd": total_collateral_base / 1e8,
                "total_debt_usd": total_debt_base / 1e8,
                "available_borrows_usd": available_borrows_base / 1e8,
                "liquidation_threshold": current_liquidation_threshold / 1e4,  # Percentage
                "ltv": ltv / 1e4,  # Percentage
                "health_factor": health_factor / 1e18,  # 18 decimals
                "positions": []  # Would need additional calls to get individual positions
            }

        except Exception as e:
            logger.error(f"Error fetching Aave V3 data: {e}")
            return None


class CompoundV3Interface(ProtocolInterface):
    """Compound V3 Protocol Interface"""

    def __init__(self, chain_id: int, rpc_url: str):
        super().__init__(chain_id, rpc_url)

        if chain_id not in COMPOUND_V3_COMET_ADDRESSES:
            raise ValueError(f"Compound V3 not supported on chain {chain_id}")

        comet_address = COMPOUND_V3_COMET_ADDRESSES[chain_id]
        self.comet_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(comet_address),
            abi=COMPOUND_V3_COMET_ABI
        )

    async def get_user_account_data(self, wallet: str) -> Optional[Dict]:
        """Get Compound V3 user account data"""
        try:
            wallet_checksum = Web3.to_checksum_address(wallet)

            # Get borrow balance
            borrow_balance = self.comet_contract.functions.borrowBalanceOf(wallet_checksum).call()

            # Get collateral balance (simplified - would need to iterate through assets)
            collateral_balance = self.comet_contract.functions.collateralBalanceOf(wallet_checksum).call()

            # Get price
            price = self.comet_contract.functions.getPrice().call()

            # Calculate USD values (simplified)
            total_debt_usd = borrow_balance / 1e6  # USDC has 6 decimals
            total_collateral_usd = (collateral_balance * price) / 1e14  # Adjust for decimals

            # Calculate health factor (simplified)
            # Compound V3 uses different liquidation logic
            liquidation_threshold = 0.8  # Typical value, varies by asset
            if total_debt_usd > 0:
                health_factor = (total_collateral_usd * liquidation_threshold) / total_debt_usd
            else:
                health_factor = float('inf')

            return {
                "total_collateral_usd": total_collateral_usd,
                "total_debt_usd": total_debt_usd,
                "available_borrows_usd": 0,  # Would need additional calculation
                "liquidation_threshold": liquidation_threshold,
                "ltv": 0.75,  # Typical value
                "health_factor": health_factor,
                "positions": []
            }

        except Exception as e:
            logger.error(f"Error fetching Compound V3 data: {e}")
            return None


class SparkInterface(AaveV3Interface):
    """Spark Protocol Interface (uses Aave V3 contracts)"""

    def __init__(self, chain_id: int, rpc_url: str):
        # Spark uses the same interface as Aave V3
        if chain_id not in SPARK_POOL_ADDRESSES:
            raise ValueError(f"Spark not supported on chain {chain_id}")

        # Override the pool address with Spark's
        ProtocolInterface.__init__(self, chain_id, rpc_url)
        pool_address = SPARK_POOL_ADDRESSES[chain_id]
        self.pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=AAVE_V3_POOL_ABI
        )


class RadiantInterface(AaveV3Interface):
    """Radiant Protocol Interface (uses Aave V2/V3 contracts)"""

    def __init__(self, chain_id: int, rpc_url: str):
        # Radiant uses similar interface to Aave
        if chain_id not in RADIANT_POOL_ADDRESSES:
            raise ValueError(f"Radiant not supported on chain {chain_id}")

        # Override the pool address with Radiant's
        ProtocolInterface.__init__(self, chain_id, rpc_url)
        pool_address = RADIANT_POOL_ADDRESSES[chain_id]
        self.pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=AAVE_V3_POOL_ABI
        )


def get_protocol_interface(
    protocol: ProtocolType,
    chain_id: int,
    rpc_url: str
) -> ProtocolInterface:
    """Factory function to get protocol interface"""

    if protocol == ProtocolType.AAVE_V3:
        return AaveV3Interface(chain_id, rpc_url)
    elif protocol == ProtocolType.COMPOUND_V3:
        return CompoundV3Interface(chain_id, rpc_url)
    elif protocol == ProtocolType.SPARK:
        return SparkInterface(chain_id, rpc_url)
    elif protocol == ProtocolType.RADIANT:
        return RadiantInterface(chain_id, rpc_url)
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")
