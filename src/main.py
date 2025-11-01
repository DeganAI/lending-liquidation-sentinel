"""
Lending Liquidation Sentinel - Monitor borrow positions and warn before liquidation risk

x402 micropayment-enabled lending position monitoring service
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging

from src.lending_monitor import LendingMonitor
from src.protocol_interfaces import ProtocolType
from src.x402_middleware_dual import X402Middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Lending Liquidation Sentinel",
    description="Monitor borrow positions and warn before liquidation risk - powered by x402",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration
payment_address = os.getenv("PAYMENT_ADDRESS", "0x01D11F7e1a46AbFC6092d7be484895D2d505095c")
base_url = os.getenv("BASE_URL", "https://lending-liquidation-sentinel-production.up.railway.app")
free_mode = os.getenv("FREE_MODE", "false").lower() == "true"

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# x402 Payment Verification Middleware
app.add_middleware(
    X402Middleware,
    payment_address=payment_address,
    base_url=base_url,
    facilitator_urls=[
        "https://facilitator.daydreams.systems",
        "https://api.cdp.coinbase.com/platform/v2/x402/facilitator"
    ],
    free_mode=free_mode,
)

# Initialize Lending Monitor
lending_monitor = LendingMonitor()
logger.info("Lending Liquidation Sentinel initialized")

if free_mode:
    logger.warning("Running in FREE MODE - no payment verification")


# Request/Response Models
class PositionFilter(BaseModel):
    """Specific position to track"""
    collateral_asset: str = Field(..., description="Collateral token address")
    debt_asset: str = Field(..., description="Debt token address")


class MonitorRequest(BaseModel):
    """Request for position monitoring"""
    wallet: str = Field(
        ...,
        description="Wallet address to monitor",
        example="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    )
    protocol_ids: List[str] = Field(
        ...,
        description="Lending protocols to check (aave_v3, compound_v3, spark, radiant)",
        example=["aave_v3", "compound_v3"]
    )
    chain_id: int = Field(
        ...,
        description="Chain ID (1=Ethereum, 137=Polygon, 42161=Arbitrum, 10=Optimism, 8453=Base, 43114=Avalanche, 56=BSC)",
        example=1
    )
    positions: Optional[List[PositionFilter]] = Field(
        None,
        description="Specific positions to track (optional, monitors all if not provided)"
    )


class MonitorResponse(BaseModel):
    """Monitoring response"""
    wallet: str
    protocol: str
    chain_id: int
    chain_name: str
    health_factor: float = Field(..., description="Current health factor (< 1.0 = liquidatable)")
    liq_price: Optional[float] = Field(None, description="Liquidation price threshold for primary collateral")
    buffer_percent: float = Field(..., description="Safety buffer percentage above liquidation")
    alert_threshold_hit: bool = Field(..., description="True if alert should fire (HF < 1.2)")
    severity: str = Field(..., description="Alert severity: safe, warning, critical")
    total_collateral_usd: float
    total_debt_usd: float
    liquidation_threshold: float
    positions: List[dict]
    timestamp: str


# Endpoints
@app.get("/", response_class=HTMLResponse)
@app.head("/")
async def root():
    """Landing page"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lending Liquidation Sentinel - Position Monitoring</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #1a0a2e 0%, #16213e 50%, #0f3460 100%);
                color: #e8f0f2;
                line-height: 1.6;
                min-height: 100vh;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            header {{
                background: linear-gradient(135deg, rgba(255, 107, 107, 0.15) 0%, rgba(255, 191, 0, 0.15) 100%);
                border: 2px solid rgba(255, 107, 107, 0.3);
                border-radius: 15px;
                padding: 40px;
                margin-bottom: 30px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
            }}
            h1 {{
                color: #ff6b6b;
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 0 2px 10px rgba(255, 107, 107, 0.3);
            }}
            .subtitle {{
                color: #ffd89c;
                font-size: 1.2em;
                margin-bottom: 15px;
            }}
            .badge {{
                display: inline-block;
                background: rgba(255, 107, 107, 0.2);
                border: 1px solid rgba(255, 107, 107, 0.4);
                color: #ff6b6b;
                padding: 6px 15px;
                border-radius: 20px;
                font-size: 0.9em;
                margin-right: 10px;
                margin-top: 10px;
                font-weight: 600;
            }}
            .section {{
                background: rgba(22, 33, 62, 0.8);
                border: 1px solid rgba(255, 107, 107, 0.2);
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
            }}
            h2 {{
                color: #ff6b6b;
                margin-bottom: 20px;
                font-size: 1.8em;
                border-bottom: 2px solid rgba(255, 107, 107, 0.3);
                padding-bottom: 10px;
            }}
            h3 {{
                color: #ffd89c;
                margin: 15px 0 10px 0;
                font-size: 1.3em;
            }}
            .endpoint {{
                background: rgba(26, 10, 46, 0.6);
                border-left: 4px solid #ff6b6b;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
            }}
            .method {{
                display: inline-block;
                background: #ff6b6b;
                color: white;
                padding: 5px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 0.85em;
                margin-right: 10px;
            }}
            .method.get {{ background: #4CAF50; }}
            code {{
                background: rgba(0, 0, 0, 0.3);
                color: #a5d6a7;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Monaco', 'Courier New', monospace;
            }}
            pre {{
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(77, 182, 172, 0.2);
                border-radius: 6px;
                padding: 15px;
                overflow-x: auto;
                margin: 10px 0;
            }}
            pre code {{
                background: none;
                padding: 0;
                display: block;
                color: #a5d6a7;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .card {{
                background: rgba(26, 10, 46, 0.6);
                border: 1px solid rgba(255, 107, 107, 0.2);
                border-radius: 10px;
                padding: 20px;
            }}
            .card h4 {{
                color: #ff6b6b;
                margin-bottom: 10px;
                font-size: 1.2em;
            }}
            .highlight {{
                color: #ff6b6b;
                font-weight: bold;
            }}
            a {{
                color: #ffbf00;
                text-decoration: none;
                border-bottom: 1px solid transparent;
                transition: all 0.3s ease;
            }}
            a:hover {{
                border-bottom-color: #ffbf00;
            }}
            footer {{
                text-align: center;
                padding: 30px 20px;
                color: #80cbc4;
                opacity: 0.8;
            }}
            .status-indicator {{
                display: inline-block;
                width: 10px;
                height: 10px;
                background: #4caf50;
                border-radius: 50%;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Lending Liquidation Sentinel</h1>
                <p class="subtitle">Monitor Your Borrow Positions Before They Get Rekt</p>
                <p style="font-size: 0.95em; color: #b8c5d6; margin: 10px 0 15px 0;">Real-time health factor monitoring across Aave, Compound, Spark, and Radiant</p>
                <div>
                    <span class="badge"><span class="status-indicator"></span>Live Monitoring</span>
                    <span class="badge">4 Protocols</span>
                    <span class="badge">7 Chains</span>
                    <span class="badge">x402 Payments</span>
                </div>
            </header>

            <div class="section">
                <h2>What is Lending Liquidation Sentinel?</h2>
                <p style="font-size: 1.1em; line-height: 1.8; margin-top: 15px;">
                    Lending Liquidation Sentinel monitors your lending positions across <span class="highlight">Aave V3, Compound V3, Spark, and Radiant</span>
                    to warn you before liquidation risk. Get alerts when your health factor drops below safe thresholds with accurate liquidation price calculations.
                </p>

                <div class="grid" style="margin-top: 30px;">
                    <div class="card">
                        <h4>Health Factor Monitoring</h4>
                        <p>Real-time health factor calculation with alerts when HF &lt; 1.2 (20% safety buffer).</p>
                    </div>
                    <div class="card">
                        <h4>Liquidation Prices</h4>
                        <p>Accurate liquidation price calculations for each collateral asset with penalty accounting.</p>
                    </div>
                    <div class="card">
                        <h4>Multi-Protocol Support</h4>
                        <p>Monitor positions across Aave V3, Compound V3, Spark, and Radiant simultaneously.</p>
                    </div>
                    <div class="card">
                        <h4>Cross-Chain Coverage</h4>
                        <p>Support for Ethereum, Polygon, Arbitrum, Optimism, Base, Avalanche, and BSC.</p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>API Endpoints</h2>

                <div class="endpoint">
                    <h3><span class="method">POST</span>/lending/monitor</h3>
                    <p>Monitor lending position health and liquidation risk</p>
                    <pre><code>curl -X POST https://your-service.railway.app/lending/monitor \\
  -H "Content-Type: application/json" \\
  -d '{{
    "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "protocol_ids": ["aave_v3", "compound_v3"],
    "chain_id": 1
  }}'</code></pre>
                </div>

                <div class="endpoint">
                    <h3><span class="method">POST</span>/entrypoints/lending-liquidation-sentinel/invoke</h3>
                    <p>AP2-compatible entrypoint for position monitoring</p>
                </div>

                <div class="endpoint">
                    <h3><span class="method get">GET</span>/health</h3>
                    <p>Health check and operational status</p>
                </div>
            </div>

            <div class="section">
                <h2>Supported Protocols</h2>
                <div class="grid">
                    <div class="card"><h4>Aave V3</h4><p>Multi-chain support on Ethereum, Polygon, Arbitrum, Optimism, Base, Avalanche</p></div>
                    <div class="card"><h4>Compound V3</h4><p>Available on Ethereum, Polygon, Arbitrum, Base</p></div>
                    <div class="card"><h4>Spark</h4><p>MakerDAO's lending protocol on Ethereum</p></div>
                    <div class="card"><h4>Radiant</h4><p>Omnichain lending on Arbitrum, Avalanche, BSC</p></div>
                </div>
            </div>

            <div class="section">
                <h2>x402 Micropayments</h2>
                <p style="margin-bottom: 20px;">
                    Uses the <strong>x402 payment protocol</strong> for usage-based billing.
                </p>

                <div class="grid">
                    <div class="card">
                        <h4>Payment Details</h4>
                        <p><strong>Price:</strong> 0.05 USDC per request</p>
                        <p><strong>Address:</strong> <code style="word-break: break-all;">{payment_address}</code></p>
                        <p><strong>Network:</strong> Base</p>
                    </div>
                    <div class="card">
                        <h4>Status</h4>
                        <p style="margin-top: 10px;"><em>{"Currently in FREE MODE for testing" if free_mode else "Payment verification active"}</em></p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Documentation</h2>
                <p style="margin-bottom: 20px;">Interactive API documentation available:</p>
                <div style="margin: 20px 0;">
                    <a href="/docs" style="display: inline-block; background: rgba(77, 182, 172, 0.2); padding: 12px 24px; border-radius: 6px; border: 1px solid #4db6ac; margin-right: 15px;">Swagger UI</a>
                    <a href="/redoc" style="display: inline-block; background: rgba(77, 182, 172, 0.2); padding: 12px 24px; border-radius: 6px; border: 1px solid #4db6ac;">ReDoc</a>
                </div>
            </div>

            <footer>
                <p><strong>Built by DeganAI</strong></p>
                <p style="margin-top: 10px; opacity: 0.7;">Bounty #9 Submission for Daydreams AI Agent Bounties</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/.well-known/agent.json")
@app.head("/.well-known/agent.json")
async def agent_metadata():
    """AP2 (Agent Payments Protocol) metadata - returns HTTP 200"""
    agent_json = {
        "name": "Lending Liquidation Sentinel",
        "description": "Monitor borrow positions and warn before liquidation risk. Track health factors and liquidation prices across Aave V3, Compound V3, Spark, and Radiant on 7+ chains.",
        "url": base_url.replace("https://", "http://") + "/",
        "version": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
            "extensions": [
                {
                    "uri": "https://github.com/google-agentic-commerce/ap2/tree/v0.1",
                    "description": "Agent Payments Protocol (AP2)",
                    "required": True,
                    "params": {
                        "roles": ["merchant"]
                    }
                }
            ]
        },
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "skills": [
            {
                "id": "lending-liquidation-sentinel",
                "name": "lending-liquidation-sentinel",
                "description": "Monitor lending position health and liquidation risk across multiple protocols",
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "streaming": False,
                "x_input_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "wallet": {
                            "description": "Wallet address to monitor",
                            "type": "string"
                        },
                        "protocol_ids": {
                            "description": "Lending protocols to check",
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "chain_id": {
                            "description": "Chain ID",
                            "type": "integer"
                        },
                        "positions": {
                            "description": "Specific positions to track",
                            "type": "array",
                            "items": {"type": "object"}
                        }
                    },
                    "required": ["wallet", "protocol_ids", "chain_id"],
                    "additionalProperties": False
                },
                "x_output_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "health_factor": {"type": "number"},
                        "liq_price": {"type": "number"},
                        "buffer_percent": {"type": "number"},
                        "alert_threshold_hit": {"type": "boolean"},
                        "severity": {"type": "string"},
                        "total_collateral_usd": {"type": "number"},
                        "total_debt_usd": {"type": "number"}
                    },
                    "required": [
                        "health_factor",
                        "buffer_percent",
                        "alert_threshold_hit",
                        "severity"
                    ],
                    "additionalProperties": False
                }
            }
        ],
        "supportsAuthenticatedExtendedCard": False,
        "entrypoints": {
            "lending-liquidation-sentinel": {
                "description": "Monitor lending position health and liquidation risk",
                "streaming": False,
                "input_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "wallet": {"description": "Wallet address", "type": "string"},
                        "protocol_ids": {"type": "array", "items": {"type": "string"}},
                        "chain_id": {"type": "integer"},
                        "positions": {"type": "array", "items": {"type": "object"}}
                    },
                    "required": ["wallet", "protocol_ids", "chain_id"],
                    "additionalProperties": False
                },
                "output_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "health_factor": {"type": "number"},
                        "liq_price": {"type": "number"},
                        "buffer_percent": {"type": "number"},
                        "alert_threshold_hit": {"type": "boolean"}
                    },
                    "additionalProperties": False
                },
                "pricing": {
                    "invoke": "0.05 USDC"
                }
            }
        },
        "payments": [
            {
                "method": "x402",
                "payee": payment_address,
                "network": "base",
                "endpoint": "https://facilitator.daydreams.systems",
                "priceModel": {
                    "default": "0.05"
                },
                "extensions": {
                    "x402": {
                        "facilitatorUrl": "https://facilitator.daydreams.systems"
                    }
                }
            }
        ]
    }

    return JSONResponse(content=agent_json, status_code=200)


@app.get("/.well-known/x402")
@app.head("/.well-known/x402")
async def x402_metadata():
    """x402 protocol metadata for service discovery"""
    metadata = {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "50000",  # 0.05 USDC (6 decimals)
                "resource": f"{base_url}/lending/monitor",
                "description": "Monitor lending position health and liquidation risk across Aave, Compound, Spark, and Radiant",
                "mimeType": "application/json",
                "payTo": payment_address,
                "maxTimeoutSeconds": 30,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
            }
        ]
    }

    return JSONResponse(content=metadata, status_code=402)


@app.get("/health")
@app.head("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "lending-liquidation-sentinel",
        "version": "1.0.0",
        "free_mode": free_mode,
        "supported_protocols": ["aave_v3", "compound_v3", "spark", "radiant"],
        "supported_chains": [1, 137, 42161, 10, 8453, 43114, 56]
    }


@app.post("/lending/monitor", response_model=MonitorResponse)
async def monitor_position(request: MonitorRequest):
    """
    Monitor lending position health and liquidation risk

    Calculates health factor, liquidation prices, and alerts for lending positions
    across Aave V3, Compound V3, Spark, and Radiant protocols.
    """
    try:
        # Validate protocol
        if not request.protocol_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one protocol_id is required"
            )

        # Monitor the first protocol (can extend to multiple)
        protocol_id = request.protocol_ids[0]

        try:
            protocol_type = ProtocolType(protocol_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid protocol: {protocol_id}. Supported: aave_v3, compound_v3, spark, radiant"
            )

        # Get position data
        logger.info(f"Monitoring position for wallet {request.wallet} on {protocol_id} (chain {request.chain_id})")

        position_data = await lending_monitor.monitor_position(
            wallet=request.wallet,
            protocol=protocol_type,
            chain_id=request.chain_id,
            position_filters=request.positions
        )

        if not position_data:
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch position data"
            )

        from datetime import datetime

        # Determine severity
        hf = position_data["health_factor"]
        if hf < 1.05:
            severity = "critical"
        elif hf < 1.2:
            severity = "warning"
        else:
            severity = "safe"

        # Calculate buffer percentage
        buffer_percent = ((hf - 1.0) / 1.0) * 100 if hf > 1.0 else 0.0

        return MonitorResponse(
            wallet=request.wallet,
            protocol=protocol_id,
            chain_id=request.chain_id,
            chain_name=position_data["chain_name"],
            health_factor=round(hf, 4),
            liq_price=position_data.get("liq_price"),
            buffer_percent=round(buffer_percent, 2),
            alert_threshold_hit=hf < 1.2,
            severity=severity,
            total_collateral_usd=round(position_data["total_collateral_usd"], 2),
            total_debt_usd=round(position_data["total_debt_usd"], 2),
            liquidation_threshold=round(position_data["liquidation_threshold"], 4),
            positions=position_data["positions"],
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Position monitoring error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/entrypoints/lending-liquidation-sentinel/invoke")
@app.head("/entrypoints/lending-liquidation-sentinel/invoke")
async def entrypoint_monitor_get():
    """x402 discovery endpoint - returns HTTP 402"""
    metadata = {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "50000",
                "resource": f"{base_url}/entrypoints/lending-liquidation-sentinel/invoke",
                "description": "Monitor lending position health and liquidation risk across Aave, Compound, Spark, and Radiant",
                "mimeType": "application/json",
                "payTo": payment_address,
                "maxTimeoutSeconds": 30,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            }
        ]
    }
    return JSONResponse(content=metadata, status_code=402)


@app.post("/entrypoints/lending-liquidation-sentinel/invoke")
async def entrypoint_monitor(request: MonitorRequest):
    """
    AP2 (Agent Payments Protocol) compatible entrypoint

    Calls the main /lending/monitor endpoint with the same logic.
    """
    return await monitor_position(request)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
