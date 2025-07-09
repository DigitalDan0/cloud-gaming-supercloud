import stripe
import requests
from typing import Dict, Optional
from decimal import Decimal
from .settings import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class BillingManager:
    def __init__(self):
        self.usd_to_usdc_rate = Decimal("1.0")  # Simplified 1:1 rate
        self.usdc_to_akt_rate = Decimal("0.5")  # Placeholder rate
        self.osmosis_api_url = "https://lcd-osmosis.keplr.app"
        self.usdc_denom = "ibc/D189335C6E4A68B513C10AB227BF1C1D38C746766278BA3EEB4FB14124F1D858"
        self.akt_denom = "ibc/1480B8FD20AD5FCAE81EA87584D269547DD4D436843C1D20F15E00EB64743EF4"
        self.osmosis_pool_id = "1135"  # USDC/AKT pool ID
    
    def create_payment_intent(self, session_hours: int = 1) -> Dict[str, str]:
        """Create Stripe payment intent for gaming session"""
        # Calculate cost: $0.05/hour as per value prop
        amount_usd = Decimal("0.05") * session_hours
        amount_cents = int(amount_usd * 100)
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata={
                    "session_hours": str(session_hours),
                    "service": "cloud-gaming"
                }
            )
            
            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "amount_usd": str(amount_usd)
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Payment creation failed: {str(e)}")
    
    def process_payment(self, payment_intent_id: str) -> Dict[str, str]:
        """Process payment and convert to AKT tokens"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status != "succeeded":
                raise Exception(f"Payment not completed: {intent.status}")
            
            # Simulate USD → USDC → AKT conversion
            usd_amount = Decimal(intent.amount) / 100
            usdc_amount = usd_amount * self.usd_to_usdc_rate
            akt_amount = usdc_amount / self.usdc_to_akt_rate
            
            # In production, this would:
            # 1. Buy USDC with USD via Stripe
            # 2. Swap USDC for AKT on DEX
            # 3. Transfer AKT to user's Akash wallet
            
            return {
                "status": "completed",
                "usd_amount": str(usd_amount),
                "usdc_amount": str(usdc_amount),
                "akt_amount": str(akt_amount),
                "transaction_id": f"stub_tx_{payment_intent_id[:8]}"
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Payment processing failed: {str(e)}")
    
    def estimate_session_cost(self, hours: int = 1) -> Dict[str, str]:
        """Estimate cost for gaming session"""
        usd_cost = Decimal("0.05") * hours
        akt_cost = (usd_cost * self.usd_to_usdc_rate) / self.usdc_to_akt_rate
        
        return {
            "hours": str(hours),
            "usd_cost": str(usd_cost),
            "akt_cost": str(akt_cost),
            "uakt_cost": str(int(akt_cost * 1_000_000))  # Convert to uakt
        }
    
    def swap_usdc_to_akt(self, usdc_amount: Decimal, sender_address: str) -> Dict[str, str]:
        """Swap USDC to AKT on Osmosis with 5% slippage buffer"""
        try:
            # Convert USDC to microunits (6 decimals)
            usdc_microunits = str(int(usdc_amount * 1_000_000))
            
            # Calculate minimum AKT output with 5% slippage buffer
            estimated_akt = usdc_amount / self.usdc_to_akt_rate
            min_akt_output = estimated_akt * Decimal("0.95")  # 5% slippage
            min_akt_microunits = str(int(min_akt_output * 1_000_000))
            
            # Prepare swap transaction message
            swap_msg = {
                "swap_exact_amount_in": {
                    "sender": sender_address,
                    "routes": [
                        {
                            "pool_id": self.osmosis_pool_id,
                            "token_out_denom": self.akt_denom
                        }
                    ],
                    "token_in": {
                        "denom": self.usdc_denom,
                        "amount": usdc_microunits
                    },
                    "token_out_min_amount": min_akt_microunits
                }
            }
            
            # Simulate API call to Osmosis
            response = requests.post(
                f"{self.osmosis_api_url}/osmosis/gamm/v1beta1/pools/{self.osmosis_pool_id}/swap_exact_amount_in",
                json=swap_msg,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Osmosis swap failed: {response.text}")
            
            swap_result = response.json()
            
            # Parse actual AKT received
            akt_received = Decimal(swap_result["token_out_amount"]) / 1_000_000
            
            return {
                "status": "completed",
                "usdc_amount": str(usdc_amount),
                "akt_received": str(akt_received),
                "min_akt_expected": str(min_akt_output),
                "slippage_used": str((estimated_akt - akt_received) / estimated_akt * 100),
                "transaction_hash": swap_result.get("tx_hash", ""),
                "pool_id": self.osmosis_pool_id
            }
            
        except requests.RequestException as e:
            raise Exception(f"Osmosis API error: {str(e)}")
        except (KeyError, ValueError) as e:
            raise Exception(f"Invalid swap response: {str(e)}")