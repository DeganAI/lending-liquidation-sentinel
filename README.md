# Lending Liquidation Sentinel

Monitor borrow positions and warn before liquidation risk across Aave V3, Compound V3, Spark, and Radiant protocols.

## Overview

Lending Liquidation Sentinel is an AI agent that monitors lending positions in real-time, calculating health factors and liquidation prices to alert users before their positions become at risk. Supports multiple DeFi lending protocols across 7 blockchain networks.

## Features

- **Real-Time Health Factor Monitoring** - Track health factors with <1.2 threshold alerts
- **Liquidation Price Calculation** - Accurate liquidation prices for each collateral asset
- **Multi-Protocol Support** - Aave V3, Compound V3, Spark, and Radiant
- **Cross-Chain Coverage** - Ethereum, Polygon, Arbitrum, Optimism, Base, Avalanche, BSC
- **x402 Payment Integration** - Micropayments via daydreams facilitator (0.05 USDC per request)

## Supported Protocols

### Aave V3
- Chains: Ethereum, Polygon, Arbitrum, Optimism, Base, Avalanche
- Most popular lending protocol with isolation mode and efficiency mode

### Compound V3
- Chains: Ethereum, Polygon, Arbitrum, Base
- Single-asset borrowing with multi-asset collateral

### Spark
- Chains: Ethereum
- MakerDAO's lending protocol

### Radiant
- Chains: Arbitrum, Avalanche, BSC
- LayerZero-powered omnichain lending

## API Endpoints

### Monitor Position
```bash
POST /lending/monitor
```

**Request:**
```json
{
  "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "protocol_ids": ["aave_v3", "compound_v3"],
  "chain_id": 1,
  "positions": [
    {
      "collateral_asset": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
      "debt_asset": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    }
  ]
}
```

**Response:**
```json
{
  "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "protocol": "aave_v3",
  "chain_id": 1,
  "chain_name": "Ethereum",
  "health_factor": 1.45,
  "liq_price": 1850.50,
  "buffer_percent": 45.0,
  "alert_threshold_hit": false,
  "severity": "safe",
  "total_collateral_usd": 10000.00,
  "total_debt_usd": 6500.00,
  "liquidation_threshold": 0.825,
  "positions": [],
  "timestamp": "2025-10-31T20:00:00Z"
}
```

### AP2 Entrypoint
```bash
POST /entrypoints/lending-liquidation-sentinel/invoke
```
Same request/response format as `/lending/monitor`

### Health Check
```bash
GET /health
```

## Health Factor Calculation

Health Factor (HF) is calculated as:
```
HF = (total_collateral_usd × liquidation_threshold) / total_debt_usd
```

- **HF > 1.2**: Safe position (>20% buffer)
- **1.05 < HF < 1.2**: Warning - consider adding collateral
- **HF < 1.05**: Critical - liquidation imminent
- **HF < 1.0**: Position can be liquidated

## Liquidation Price

For single-asset collateral positions:
```
liq_price = (debt × debt_price) / (collateral × liquidation_threshold)
```

Accounts for:
- Liquidation threshold (protocol-specific)
- Liquidation bonus/penalty (typically 5%)
- Multi-asset weighted averages

## Installation

```bash
# Clone repository
git clone https://github.com/DeganAI/lending-liquidation-sentinel.git
cd lending-liquidation-sentinel

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PORT=8000
export FREE_MODE=true
export BASE_URL=http://localhost:8000

# Run locally
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

- `PORT` - Server port (default: 8000)
- `FREE_MODE` - Skip payment verification for testing (default: false)
- `PAYMENT_ADDRESS` - Payment wallet address
- `BASE_URL` - Base URL for the service
- `CHAIN_1_RPC_URL` - Ethereum RPC URL (optional, uses public RPC by default)
- `CHAIN_137_RPC_URL` - Polygon RPC URL (optional)
- `CHAIN_42161_RPC_URL` - Arbitrum RPC URL (optional)

## Deployment

See [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) for Railway deployment instructions.

## x402 Payments

This service uses the x402 micropayment protocol:

- **Price**: 0.05 USDC per request
- **Network**: Base
- **Payment Address**: `0x01D11F7e1a46AbFC6092d7be484895D2d505095c`
- **Facilitator**: https://facilitator.daydreams.systems

## Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test monitoring (requires valid wallet with position)
curl -X POST http://localhost:8000/lending/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "protocol_ids": ["aave_v3"],
    "chain_id": 1
  }'
```

## License

MIT

## Credits

Built by DeganAI for the Daydreams AI Agent Bounties program (Bounty #9).
# trigger
# trigger
