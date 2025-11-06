import { createAgentApp } from "@lucid-agents/agent-kit";
import { Hono } from "hono";
import { z } from "zod";
import { createPublicClient, http } from "viem";
import { mainnet, arbitrum, optimism, polygon, base, avalanche, bsc } from "viem/chains";

// Input schema
const LiquidationInputSchema = z.object({
  wallet_address: z.string().describe("Wallet address to monitor"),
  chain_ids: z.array(z.number()).describe("Chain IDs to check (1, 42161, 10, 137, 8453, 43114, 56)"),
  protocols: z.array(z.string()).describe("Protocols to monitor (aave, compound, spark, radiant)"),
  alert_threshold: z.number().optional().default(1.5).describe("Health factor threshold for alerts (default: 1.5)"),
});

// Output schema
const LiquidationOutputSchema = z.object({
  positions: z.array(z.object({
    protocol: z.string(),
    chain_id: z.number(),
    health_factor: z.number(),
    liquidation_price: z.number().nullable(),
    collateral_usd: z.number(),
    debt_usd: z.number(),
    risk_level: z.string(),
    warning: z.string().nullable(),
  })),
  total_positions: z.number(),
  at_risk_count: z.number(),
  timestamp: z.string(),
});

const { app, addEntrypoint, config } = createAgentApp(
  {
    name: "Lending Liquidation Sentinel",
    version: "1.0.0",
    description: "Monitor borrow positions and warn before liquidation risk across multiple chains",
  },
  {
    config: {
      payments: {
        facilitatorUrl: "https://facilitator.daydreams.systems",
        payTo: "0x01D11F7e1a46AbFC6092d7be484895D2d505095c",
        network: "base",
        asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        defaultPrice: "$0.06", // 0.06 USDC
      },
    },
    useConfigPayments: true,
    ap2: {
      required: true,
      params: { roles: ["merchant"] },
    },
  }
);

// Chain configuration
const CHAIN_CONFIGS: Record<number, any> = {
  1: { chain: mainnet, rpc: "https://eth.llamarpc.com" },
  42161: { chain: arbitrum, rpc: "https://arb1.arbitrum.io/rpc" },
  10: { chain: optimism, rpc: "https://mainnet.optimism.io" },
  137: { chain: polygon, rpc: "https://polygon-rpc.com" },
  8453: { chain: base, rpc: "https://mainnet.base.org" },
  43114: { chain: avalanche, rpc: "https://api.avax.network/ext/bc/C/rpc" },
  56: { chain: bsc, rpc: "https://bsc-dataseed1.binance.org" },
};

// Create viem clients lazily to avoid startup issues
const clients: Record<number, ReturnType<typeof createPublicClient>> = {};

function getClient(chainId: number) {
  if (!clients[chainId]) {
    const config = CHAIN_CONFIGS[chainId];
    if (!config) {
      throw new Error(`Chain ${chainId} not supported`);
    }
    clients[chainId] = createPublicClient({
      chain: config.chain,
      transport: http(config.rpc),
    });
  }
  return clients[chainId];
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

async function getAavePosition(address: string, chainId: number, threshold: number): Promise<LendingPosition | null> {
  try {
    const AAVE_POOL_V3: Record<number, string> = {
      1: "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
      42161: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
      10: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
      137: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
      8453: "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    };

    const poolAddress = AAVE_POOL_V3[chainId];
    if (!poolAddress) return null;

    const client = getClient(chainId);
    const data = (await client.readContract({
      address: poolAddress as `0x${string}`,
      abi: [
        {
          name: "getUserAccountData",
          type: "function",
          stateMutability: "view",
          inputs: [{ name: "user", type: "address" }],
          outputs: [
            { name: "totalCollateralBase", type: "uint256" },
            { name: "totalDebtBase", type: "uint256" },
            { name: "availableBorrowsBase", type: "uint256" },
            { name: "currentLiquidationThreshold", type: "uint256" },
            { name: "ltv", type: "uint256" },
            { name: "healthFactor", type: "uint256" },
          ],
        },
      ],
      functionName: "getUserAccountData",
      args: [address as `0x${string}`],
    })) as any[];

    const collateralUsd = Number(data[0]) / 1e8;
    const debtUsd = Number(data[1]) / 1e8;
    const healthFactor = Number(data[5]) / 1e18;

    if (collateralUsd === 0 && debtUsd === 0) return null;

    let riskLevel = "safe";
    let warning = null;

    if (healthFactor < 1.0) {
      riskLevel = "critical";
      warning = "🚨 LIQUIDATION IMMINENT - Health factor < 1.0";
    } else if (healthFactor < 1.2) {
      riskLevel = "high";
      warning = "⚠️ HIGH RISK - Health factor < 1.2";
    } else if (healthFactor < threshold) {
      riskLevel = "moderate";
      warning = `ℹ️ Monitor closely - Health factor < ${threshold}`;
    }

    return {
      protocol: "Aave V3",
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

async function getCompoundV3Position(address: string, chainId: number, threshold: number): Promise<LendingPosition | null> {
  try {
    const COMPOUND_V3_COMET: Record<number, string> = {
      1: "0xc3d688B66703497DAA19211EEdff47f25384cdc3", // cUSDCv3
      42161: "0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA",
      137: "0xF25212E676D1F7F89Cd72fFEe66158f541246445",
      8453: "0x9c4ec768c28520B50860ea7a15bd7213a9fF58bf",
    };

    const cometAddress = COMPOUND_V3_COMET[chainId];
    if (!cometAddress) return null;

    const client = getClient(chainId);
    const collateralData = (await client.readContract({
      address: cometAddress as `0x${string}`,
      abi: [
        {
          name: "getSupplyBalance",
          type: "function",
          stateMutability: "view",
          inputs: [{ name: "account", type: "address" }],
          outputs: [{ name: "", type: "uint256" }],
        },
      ],
      functionName: "getSupplyBalance",
      args: [address as `0x${string}`],
    })) as bigint;

    const borrowData = (await client.readContract({
      address: cometAddress as `0x${string}`,
      abi: [
        {
          name: "getBorrowBalance",
          type: "function",
          stateMutability: "view",
          inputs: [{ name: "account", type: "address" }],
          outputs: [{ name: "", type: "uint256" }],
        },
      ],
      functionName: "getBorrowBalance",
      args: [address as `0x${string}`],
    })) as bigint;

    const collateralUsd = Number(collateralData) / 1e6; // USDC has 6 decimals
    const debtUsd = Number(borrowData) / 1e6;

    if (collateralUsd === 0 && debtUsd === 0) return null;

    const healthFactor = debtUsd > 0 ? (collateralUsd * 0.85) / debtUsd : 999;

    let riskLevel = "safe";
    let warning = null;

    if (healthFactor < 1.0) {
      riskLevel = "critical";
      warning = "🚨 LIQUIDATION IMMINENT - Health factor < 1.0";
    } else if (healthFactor < 1.2) {
      riskLevel = "high";
      warning = "⚠️ HIGH RISK - Health factor < 1.2";
    } else if (healthFactor < threshold) {
      riskLevel = "moderate";
      warning = `ℹ️ Monitor closely - Health factor < ${threshold}`;
    }

    return {
      protocol: "Compound V3",
      chain_id: chainId,
      health_factor: healthFactor,
      liquidation_price: null,
      collateral_usd: collateralUsd,
      debt_usd: debtUsd,
      risk_level: riskLevel,
      warning,
    };
  } catch (error) {
    console.error(`[COMPOUND] Error fetching position on chain ${chainId}:`, error);
    return null;
  }
}

async function getLendingPositions(
  walletAddress: string,
  chainIds: number[],
  protocols: string[],
  threshold: number
): Promise<LendingPosition[]> {
  const positions: LendingPosition[] = [];

  for (const chainId of chainIds) {
    if (!CHAIN_CONFIGS[chainId]) {
      console.warn(`[FETCH] Chain ${chainId} not supported`);
      continue;
    }

    for (const protocol of protocols) {
      try {
        const protocolLower = protocol.toLowerCase();
        if (protocolLower === "aave") {
          const position = await getAavePosition(walletAddress, chainId, threshold);
          if (position) positions.push(position);
        } else if (protocolLower === "compound") {
          const position = await getCompoundV3Position(walletAddress, chainId, threshold);
          if (position) positions.push(position);
        }
      } catch (error) {
        console.error(`[${protocol}] Error on chain ${chainId}:`, error);
      }
    }
  }

  return positions;
}

// Register entrypoint
addEntrypoint({
  key: "lending-liquidation-sentinel",
  description: "Monitor lending positions and warn before liquidation risk across Aave V3 and Compound V3",
  input: LiquidationInputSchema,
  output: LiquidationOutputSchema,
  price: "$0.06", // 0.06 USDC
  async handler({ input }) {
    const positions = await getLendingPositions(
      input.wallet_address,
      input.chain_ids,
      input.protocols,
      input.alert_threshold
    );

    const atRiskCount = positions.filter((p) => p.health_factor < input.alert_threshold).length;

    return {
      output: {
        positions,
        total_positions: positions.length,
        at_risk_count: atRiskCount,
        timestamp: new Date().toISOString(),
      },
    };
  },
});

// Create wrapper app for internal API
const wrapperApp = new Hono();

// Internal API endpoint (no payment required)
wrapperApp.post("/api/internal/lending-liquidation-sentinel", async (c) => {
  try {
    // Check API key authentication
    const apiKey = c.req.header("X-Internal-API-Key");
    const expectedKey = process.env.INTERNAL_API_KEY;

    if (!expectedKey) {
      console.error("[INTERNAL API] INTERNAL_API_KEY not set");
      return c.json({ error: "Server configuration error" }, 500);
    }

    if (apiKey !== expectedKey) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    // Get input from request body
    const input = await c.req.json();

    // Validate input
    const validatedInput = LiquidationInputSchema.parse(input);

    // Call the same logic as x402 endpoint
    const positions = await getLendingPositions(
      validatedInput.wallet_address,
      validatedInput.chain_ids,
      validatedInput.protocols,
      validatedInput.alert_threshold
    );

    const atRiskCount = positions.filter((p) => p.health_factor < validatedInput.alert_threshold).length;

    return c.json({
      positions,
      total_positions: positions.length,
      at_risk_count: atRiskCount,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[INTERNAL API] Error:", error);
    return c.json({ error: error instanceof Error ? error.message : "Internal error" }, 500);
  }
});

// Mount the x402 agent app (public, requires payment)
wrapperApp.route("/", app);

// Export for Bun
export default {
  port: parseInt(process.env.PORT || "3000"),
  fetch: wrapperApp.fetch,
};

// Bun server start
console.log(`🚀 Lending Liquidation Sentinel running on port ${process.env.PORT || 3000}`);
console.log(`📝 Manifest: ${process.env.BASE_URL}/.well-known/agent.json`);
console.log(`💰 Payment address: ${config.payments?.payTo}`);
console.log(`🔓 Internal API: /api/internal/lending-liquidation-sentinel (requires API key)`);



