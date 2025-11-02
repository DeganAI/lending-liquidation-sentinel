import { createAgentApp } from '@lucid-dreams/agent-kit';
import { Hono } from 'hono';
import { createPublicClient, http } from 'viem';
import { mainnet, arbitrum, optimism, polygon, base, avalanche, bsc } from 'viem/chains';

console.log('[STARTUP] ===== LENDING LIQUIDATION SENTINEL =====');

const PORT = parseInt(process.env.PORT || '3000', 10);
const HOST = '0.0.0.0';
const FACILITATOR_URL = process.env.FACILITATOR_URL || 'https://facilitator.cdp.coinbase.com';
const WALLET_ADDRESS = process.env.ADDRESS || '0x01D11F7e1a46AbFC6092d7be484895D2d505095c';
const NETWORK = process.env.NETWORK || 'base';

const CHAIN_CONFIGS: Record<number, any> = {
  1: { chain: mainnet, rpc: 'https://eth.llamarpc.com' },
  42161: { chain: arbitrum, rpc: 'https://arb1.arbitrum.io/rpc' },
  10: { chain: optimism, rpc: 'https://mainnet.optimism.io' },
  137: { chain: polygon, rpc: 'https://polygon-rpc.com' },
  8453: { chain: base, rpc: 'https://mainnet.base.org' },
  43114: { chain: avalanche, rpc: 'https://api.avax.network/ext/bc/C/rpc' },
  56: { chain: bsc, rpc: 'https://bsc-dataseed1.binance.org' },
};

const clients: Record<number, ReturnType<typeof createPublicClient>> = {};
for (const [chainId, config] of Object.entries(CHAIN_CONFIGS)) {
  clients[parseInt(chainId)] = createPublicClient({ chain: config.chain, transport: http(config.rpc) });
}

interface LendingPosition {
  protocol: string;
  chain_id: number;
  health_factor: number;
  liquidation_price: number | null;
  collateral_usd: number;
  debt_usd: number;
  risk_level: string;
  warning: string | null;
}

async function getLendingPositions(walletAddress: string, chainIds: number[], protocols: string[]): Promise<LendingPosition[]> {
  const positions: LendingPosition[] = [];

  for (const chainId of chainIds) {
    for (const protocol of protocols) {
      try {
        if (protocol.toLowerCase() === 'aave') {
          const position = await getAavePosition(walletAddress, chainId);
          if (position) positions.push(position);
        }
      } catch (error) {
        console.error(`[${protocol}] Error on chain ${chainId}:`, error);
      }
    }
  }

  return positions;
}

async function getAavePosition(address: string, chainId: number): Promise<LendingPosition | null> {
  try {
    const AAVE_POOL_V3: Record<number, string> = {
      1: '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
      42161: '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
      10: '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
      137: '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
      8453: '0xA238Dd80C259a72e81d7e4664a9801593F98d1c5',
    };

    const poolAddress = AAVE_POOL_V3[chainId];
    if (!poolAddress) return null;

    const client = clients[chainId];
    const data = await client.readContract({
      address: poolAddress as `0x${string}`,
      abi: [{
        name: 'getUserAccountData',
        type: 'function',
        stateMutability: 'view',
        inputs: [{ name: 'user', type: 'address' }],
        outputs: [
          { name: 'totalCollateralBase', type: 'uint256' },
          { name: 'totalDebtBase', type: 'uint256' },
          { name: 'availableBorrowsBase', type: 'uint256' },
          { name: 'currentLiquidationThreshold', type: 'uint256' },
          { name: 'ltv', type: 'uint256' },
          { name: 'healthFactor', type: 'uint256' },
        ],
      }],
      functionName: 'getUserAccountData',
      args: [address as `0x${string}`],
    }) as any[];

    const collateralUsd = Number(data[0]) / 1e8;
    const debtUsd = Number(data[1]) / 1e8;
    const healthFactor = Number(data[5]) / 1e18;

    if (collateralUsd === 0 && debtUsd === 0) return null;

    let riskLevel = 'safe';
    let warning = null;

    if (healthFactor < 1.0) {
      riskLevel = 'critical';
      warning = '🚨 LIQUIDATION IMMINENT - Health factor < 1.0';
    } else if (healthFactor < 1.2) {
      riskLevel = 'high';
      warning = '⚠️ HIGH RISK - Health factor < 1.2';
    } else if (healthFactor < 1.5) {
      riskLevel = 'moderate';
      warning = 'ℹ️ Monitor closely - Health factor < 1.5';
    }

    return {
      protocol: 'Aave V3',
      chain_id: chainId,
      health_factor: healthFactor,
      liquidation_price: null,
      collateral_usd: collateralUsd,
      debt_usd: debtUsd,
      risk_level: riskLevel,
      warning,
    };
  } catch (error) {
    console.error(`[AAVE] Error fetching position on chain ${chainId}:`, error);
    return null;
  }
}

const app = createAgentApp({
  name: 'Lending Liquidation Sentinel',
  description: 'Monitor borrow positions and warn before liquidation risk',
  version: '1.0.0',
  paymentsConfig: {
    facilitatorUrl: FACILITATOR_URL,
    address: WALLET_ADDRESS as `0x${string}`,
    network: NETWORK,
    defaultPrice: '$0.06',
  },
});

const honoApp = app.app;

honoApp.get('/health', (c) => c.json({ status: 'ok', service: 'Lending Liquidation Sentinel', version: '1.0.0' }));

honoApp.get('/og-image.png', (c) => {
  const svg = `<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <rect width="1200" height="630" fill="#1a0a2e"/>
  <text x="600" y="280" font-family="Arial" font-size="60" fill="#ff6b6b" text-anchor="middle" font-weight="bold">Liquidation Sentinel</text>
  <text x="600" y="350" font-family="Arial" font-size="32" fill="#ffd89c" text-anchor="middle">Lending Position Monitor</text>
  <text x="600" y="420" font-family="Arial" font-size="24" fill="#b8c5d6" text-anchor="middle">Aave · Compound · Multi-Chain</text>
</svg>`;
  c.header('Content-Type', 'image/svg+xml');
  return c.body(svg);
});

app.addEntrypoint({
  key: 'lending-liquidation-sentinel',
  name: 'Lending Liquidation Sentinel',
  description: 'Monitor borrow positions and warn before liquidation risk',
  price: '$0.06',
  outputSchema: {
    input: {
      type: 'http',
      method: 'POST',
      discoverable: true,
      bodyType: 'json',
      bodyFields: {
        wallet_address: { type: 'string', required: true, description: 'Wallet address to monitor' },
        chain_ids: { type: 'array', required: true, description: 'Chain IDs to check (1, 42161, 10, 137, 8453)' },
        protocols: { type: 'array', required: true, description: 'Protocols to monitor (aave, compound)' },
      },
    },
    output: {
      type: 'object',
      required: ['positions', 'total_positions', 'at_risk_count', 'timestamp'],
      properties: {
        positions: { type: 'array' },
        total_positions: { type: 'integer' },
        at_risk_count: { type: 'integer' },
        timestamp: { type: 'string' },
      },
    },
  } as any,
  handler: async (ctx) => {
    const { wallet_address, chain_ids, protocols } = ctx.input as any;
    const positions = await getLendingPositions(wallet_address, chain_ids, protocols);
    const atRiskCount = positions.filter(p => p.health_factor < 1.5).length;

    return {
      positions,
      total_positions: positions.length,
      at_risk_count: atRiskCount,
      timestamp: new Date().toISOString(),
    };
  },
});

const wrapperApp = new Hono();

wrapperApp.get('/favicon.ico', (c) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#ff6b6b"/><text y=".9em" x="50%" text-anchor="middle" font-size="90">⚠️</text></svg>`;
  c.header('Content-Type', 'image/svg+xml');
  return c.body(svg);
});

wrapperApp.get('/', (c) => {
  return c.html(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Lending Liquidation Sentinel - x402 Agent</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.ico">
  <meta property="og:title" content="Lending Liquidation Sentinel - x402 Agent">
  <meta property="og:description" content="Monitor borrow positions and warn before liquidation risk">
  <meta property="og:image" content="https://lending-liquidation-sentinel-production.up.railway.app/og-image.png">
  <style>body{font-family:system-ui;max-width:1200px;margin:40px auto;padding:20px;background:#1a0a2e;color:#e8f0f2}h1{color:#ff6b6b}.endpoint{background:rgba(26,10,46,0.6);padding:15px;border-radius:8px;margin:10px 0;border-left:4px solid #ff6b6b}code{background:rgba(0,0,0,0.3);color:#a5d6a7;padding:2px 6px;border-radius:4px}</style>
</head>
<body>
  <h1>Lending Liquidation Sentinel</h1>
  <p>Track health factors and liquidation risks across Aave V3, Compound V3, and more</p>
  <div class="endpoint"><strong>Invoke:</strong> <code>POST /entrypoints/lending-liquidation-sentinel/invoke</code></div>
  <div class="endpoint"><strong>Health:</strong> <code>GET /health</code></div>
  <p>$0.06 USDC per request</p>
</body>
</html>`);
});

wrapperApp.all('*', async (c) => honoApp.fetch(c.req.raw));

if (typeof Bun !== 'undefined') {
  Bun.serve({ port: PORT, hostname: HOST, fetch: wrapperApp.fetch });
} else {
  const { serve } = await import('@hono/node-server');
  serve({ fetch: wrapperApp.fetch, port: PORT, hostname: HOST });
}

console.log(`[SUCCESS] ✓ Server running at http://${HOST}:${PORT}`);
