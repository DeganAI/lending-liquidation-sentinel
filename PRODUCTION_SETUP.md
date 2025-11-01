# Production Setup Guide

Complete guide to deploying Lending Liquidation Sentinel to Railway and registering on x402scan.

## Prerequisites

- GitHub account
- Railway account (https://railway.app)
- Git installed locally

## Step 1: Create GitHub Repository

```bash
# Navigate to project directory
cd /path/to/lending-liquidation-sentinel

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit - Lending Liquidation Sentinel"

# Create repository on GitHub
# Go to https://github.com/new
# Repository name: lending-liquidation-sentinel
# Keep it public

# Add remote and push
git remote add origin https://github.com/YOUR_USERNAME/lending-liquidation-sentinel.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy to Railway

### 2.1 Create New Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authenticate with GitHub
5. Select `lending-liquidation-sentinel` repository

### 2.2 Configure Environment Variables

In Railway dashboard, add these environment variables:

```bash
PORT=8000
FREE_MODE=false
PAYMENT_ADDRESS=0x01D11F7e1a46AbFC6092d7be484895D2d505095c
BASE_URL=https://lending-liquidation-sentinel-production.up.railway.app

# Optional: Custom RPC URLs for better reliability
CHAIN_1_RPC_URL=https://eth.llamarpc.com
CHAIN_137_RPC_URL=https://polygon.llamarpc.com
CHAIN_42161_RPC_URL=https://arbitrum.llamarpc.com
CHAIN_10_RPC_URL=https://optimism.llamarpc.com
CHAIN_8453_RPC_URL=https://base.llamarpc.com
CHAIN_43114_RPC_URL=https://avalanche.llamarpc.com
CHAIN_56_RPC_URL=https://binance.llamarpc.com
```

**Important Notes:**
- `FREE_MODE=false` enables payment verification
- `BASE_URL` should match your Railway domain
- RPC URLs are optional - service will use public RPCs if not provided

### 2.3 Deploy

Railway will automatically:
1. Detect `railway.toml` configuration
2. Build using Dockerfile
3. Deploy the service
4. Assign a public URL

Wait for deployment to complete (usually 2-3 minutes).

## Step 3: Verify Deployment

### 3.1 Check Health Endpoint

```bash
# Replace with your Railway URL
curl https://lending-liquidation-sentinel-production.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "lending-liquidation-sentinel",
  "version": "1.0.0",
  "free_mode": false,
  "supported_protocols": ["aave_v3", "compound_v3", "spark", "radiant"],
  "supported_chains": [1, 137, 42161, 10, 8453, 43114, 56]
}
```

### 3.2 Verify agent.json (HTTP 200)

```bash
curl -I https://lending-liquidation-sentinel-production.up.railway.app/.well-known/agent.json
```

Should return `HTTP/2 200`

### 3.3 Verify x402 Metadata (HTTP 402)

```bash
curl -I https://lending-liquidation-sentinel-production.up.railway.app/.well-known/x402
```

Should return `HTTP/2 402`

### 3.4 Test Entrypoint (HTTP 402 without payment)

```bash
curl -s https://lending-liquidation-sentinel-production.up.railway.app/entrypoints/lending-liquidation-sentinel/invoke \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "protocol_ids": ["aave_v3"],
    "chain_id": 1
  }' | jq
```

Should return x402 payment required response with all required fields.

## Step 4: Register on x402scan

### 4.1 Register Service

1. Go to https://www.x402scan.com/resources/register
2. Enter your entrypoint URL:
   ```
   https://lending-liquidation-sentinel-production.up.railway.app/entrypoints/lending-liquidation-sentinel/invoke
   ```
3. Leave headers blank
4. Click "Add"

### 4.2 Verify Registration

1. Should see "Resource Added" confirmation
2. Visit https://www.x402scan.com
3. Search for your service to confirm it's listed

## Step 5: Test with Payment (Optional)

If you want to test the full payment flow:

```bash
# 1. Send 0.05 USDC to payment address on Base
# Payment Address: 0x01D11F7e1a46AbFC6092d7be484895D2d505095c

# 2. Make request with transaction hash
curl -X POST https://lending-liquidation-sentinel-production.up.railway.app/lending/monitor \
  -H "Content-Type: application/json" \
  -H "X-Payment-TxHash: YOUR_TX_HASH" \
  -d '{
    "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "protocol_ids": ["aave_v3"],
    "chain_id": 1
  }'
```

## Monitoring and Maintenance

### View Logs

In Railway dashboard:
1. Select your project
2. Click "Deployments" tab
3. Click on latest deployment
4. View real-time logs

### Update Service

```bash
# Make changes locally
git add .
git commit -m "Update: description of changes"
git push origin main
```

Railway will automatically redeploy on push to main branch.

### Rollback

In Railway dashboard:
1. Go to "Deployments" tab
2. Click on previous successful deployment
3. Click "Redeploy"

## Troubleshooting

### Service Won't Start

Check Railway logs for errors:
- Missing environment variables
- Python dependency issues
- Port binding errors

### 502 Bad Gateway

- Service may still be starting (wait 30 seconds)
- Check health check endpoint is responding
- Verify PORT environment variable is set

### x402 Registration Fails

Verify:
- Entrypoint returns HTTP 402 (not 200 or 500)
- Response includes all required x402 fields
- URL is publicly accessible
- Response is valid JSON

### RPC Connection Issues

- Check RPC URLs are valid and accessible
- Consider using paid RPC providers (Alchemy, Infura) for production
- Verify chain IDs match network configurations

## Performance Optimization

### RPC Providers

For production, use dedicated RPC providers:

- **Alchemy**: https://www.alchemy.com
- **Infura**: https://www.infura.io
- **QuickNode**: https://www.quicknode.com

Set custom RPC URLs in environment variables for better reliability and rate limits.

### Scaling

Railway auto-scales based on traffic. For high-volume usage:

1. Increase worker count in `railway.toml`:
   ```toml
   startCommand = "gunicorn src.main:app -w 8 -k uvicorn.workers.UvicornWorker ..."
   ```

2. Enable autoscaling in Railway dashboard

3. Consider caching for frequently accessed positions

## Security Best Practices

1. **Never commit secrets** - Use environment variables
2. **Use HTTPS** - Railway provides SSL automatically
3. **Rate limiting** - Consider adding rate limits for production
4. **Monitor payment address** - Regularly check payment wallet
5. **Keep dependencies updated** - Run `pip list --outdated` regularly

## Support

- **GitHub Issues**: https://github.com/DeganAI/lending-liquidation-sentinel/issues
- **Daydreams Discord**: https://discord.gg/daydreams
- **x402 Documentation**: https://www.x402scan.com

## Next Steps

1. Monitor service health and logs
2. Test with real lending positions
3. Submit bounty PR to daydreamsai/agent-bounties
4. Share service URL with community
