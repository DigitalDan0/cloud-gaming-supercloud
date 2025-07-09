# Cloud Gaming Supercloud MVP

> Spin up a Chicago GPU in 90s, play any PC game at 1080p/120fps for 40-70% less than GeForce NOW.

An Akash-backed cloud gaming platform that provisions GPU instances for streaming PC games via Sunshine/Moonlight.

## Architecture

- **Broker Service**: FastAPI web service that manages Akash leases and billing
- **Gaming Container**: Ubuntu 22.04 + NVIDIA drivers + Sunshine + SteamCMD + Proton
- **Akash Network**: Decentralized compute provider for GPU instances

## Quick Start

### Development Environment

1. Open in VS Code with DevContainer support
2. The DevContainer will automatically install Akash CLI and dependencies
3. Start the broker: `cd broker && python -m uvicorn main:app --reload`
4. API available at: `http://localhost:8000`

### Manual Setup

```bash
# Install dependencies
pip install fastapi uvicorn pytest pytest-mock stripe python-multipart

# Install Akash CLI
curl -sSfL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | sh
sudo mv ./bin/akash /usr/local/bin/

# Run tests
pytest tests/ -v

# Start broker
cd broker && python -m uvicorn main:app --reload
```

## Environment Variables

### Required

```bash
# Akash configuration
AKASH_FROM=your-akash-key-name                    # Your Akash wallet key name
STRIPE_SECRET_KEY=sk_test_your_stripe_secret      # Stripe secret key

# Additional required for production
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret   # Stripe webhook secret
```

### Optional

```bash
# Akash network settings
AKASH_NODE=https://rpc.akash.forbole.com:443     # Akash RPC node
AKASH_CHAIN_ID=akashnet-2                        # Akash chain ID
AKASH_KEYRING_BACKEND=os                         # Keyring backend

# Pricing
LEASE_PRICE_UAKT=5000                           # Price per hour in uakt

# Gaming configuration
SUNSHINE_PORT=47984                             # Sunshine TCP port
SUNSHINE_UDP_PORT=47989                         # Sunshine UDP port

# API settings
API_HOST=0.0.0.0                               # API bind host
API_PORT=8000                                  # API bind port
```

## API Endpoints

### Create Gaming Session
```bash
curl -X POST "http://localhost:8000/sessions" \
  -H "Content-Type: application/json" \
  -d '{"hours": 1, "payment_method": "stripe"}'
```

### Get Session Status
```bash
curl "http://localhost:8000/sessions/{session_id}"
```

### Close Session
```bash
curl -X DELETE "http://localhost:8000/sessions/{session_id}"
```

## Deployment

### Build Gaming Container
```bash
cd images/ubuntu-sunshine
docker build -t gaming-sunshine .
```

### Validate SDL Template
```bash
akash validate sdl/sunshine.yaml
```

### Deploy to Akash
```bash
akash tx deployment create sdl/sunshine.yaml \
  --from your-key-name \
  --gas auto \
  --gas-adjustment 1.4
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=broker --cov-report=term-missing

# Run specific test
pytest tests/test_lease_manager.py::TestLeaseManager::test_create_lease_success -v
```

## Container Health Checks

The gaming container includes health checks to verify:
- NVENC hardware encoding support
- Sunshine streaming server status
- Prometheus metrics endpoint

## Pricing Model

- **Target Cost**: $0.05/hour (40-70% less than GeForce NOW)
- **Akash Pricing**: 5000 uakt/hour
- **Payment Flow**: USD → USDC → AKT (automated via Stripe)

## Security Notes

- Never commit API keys or secrets to the repository
- Use environment variables for all sensitive configuration
- Akash wallet keys should be stored securely using the keyring backend
- Production deployments should use hardware security modules

## Contributing

1. All code must pass `black` formatting and `pylint` checks
2. Tests required for new features
3. Commit messages in present tense imperative
4. Follow PEP-8 style guidelines

## CI/CD

GitHub Actions workflow:
1. **Test**: Run pytest suite with mocked subprocess calls
2. **Build**: Create and push container image to GHCR
3. **Validate**: Verify SDL template with Akash CLI
4. **Deploy**: Deploy to staging environment (main branch only)

## License

MIT