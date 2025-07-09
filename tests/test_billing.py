import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from broker.billing import BillingManager

class TestBillingManager:
    
    @pytest.fixture
    def billing_manager(self):
        return BillingManager()
    
    @pytest.fixture
    def mock_requests_post(self):
        with patch('broker.billing.requests.post') as mock_post:
            yield mock_post
    
    def test_swap_usdc_to_akt_success(self, billing_manager, mock_requests_post):
        """Test successful USDC to AKT swap on Osmosis"""
        # Mock successful Osmosis response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_out_amount": "190000000",  # 190 AKT in microunits
            "tx_hash": "0x123abc456def789"
        }
        mock_requests_post.return_value = mock_response
        
        result = billing_manager.swap_usdc_to_akt(
            usdc_amount=Decimal("100.0"),
            sender_address="osmo1test123"
        )
        
        # Verify result
        assert result["status"] == "completed"
        assert result["usdc_amount"] == "100.0"
        assert result["akt_received"] == "190.0"
        assert result["min_akt_expected"] == "190.0"  # 200 * 0.95
        assert result["transaction_hash"] == "0x123abc456def789"
        assert result["pool_id"] == "1135"
        
        # Verify API call was made correctly
        mock_requests_post.assert_called_once()
        call_args = mock_requests_post.call_args
        
        # Check URL
        expected_url = f"{billing_manager.osmosis_api_url}/osmosis/gamm/v1beta1/pools/1135/swap_exact_amount_in"
        assert call_args[0][0] == expected_url
        
        # Check request body
        swap_msg = call_args[1]["json"]["swap_exact_amount_in"]
        assert swap_msg["sender"] == "osmo1test123"
        assert swap_msg["token_in"]["amount"] == "100000000"  # 100 USDC in microunits
        assert swap_msg["token_in"]["denom"] == billing_manager.usdc_denom
        assert swap_msg["token_out_min_amount"] == "190000000"  # 190 AKT min (5% slippage)
        assert swap_msg["routes"][0]["pool_id"] == "1135"
        assert swap_msg["routes"][0]["token_out_denom"] == billing_manager.akt_denom
    
    def test_swap_usdc_to_akt_with_slippage(self, billing_manager, mock_requests_post):
        """Test swap with actual slippage calculation"""
        # Mock response with less AKT than expected (slippage occurred)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_out_amount": "180000000",  # 180 AKT (10% slippage)
            "tx_hash": "0xslippage123"
        }
        mock_requests_post.return_value = mock_response
        
        result = billing_manager.swap_usdc_to_akt(
            usdc_amount=Decimal("100.0"),
            sender_address="osmo1test123"
        )
        
        # Verify slippage calculation
        expected_akt = Decimal("200.0")  # 100 / 0.5 rate
        actual_akt = Decimal("180.0")
        expected_slippage = (expected_akt - actual_akt) / expected_akt * 100
        
        assert result["status"] == "completed"
        assert result["akt_received"] == "180.0"
        assert result["slippage_used"] == str(expected_slippage)
        assert float(result["slippage_used"]) == 10.0  # 10% slippage
    
    def test_swap_usdc_to_akt_api_error(self, billing_manager, mock_requests_post):
        """Test handling of Osmosis API error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_requests_post.return_value = mock_response
        
        with pytest.raises(Exception, match="Osmosis swap failed"):
            billing_manager.swap_usdc_to_akt(
                usdc_amount=Decimal("100.0"),
                sender_address="osmo1test123"
            )
    
    def test_swap_usdc_to_akt_network_error(self, billing_manager, mock_requests_post):
        """Test handling of network errors"""
        mock_requests_post.side_effect = Exception("Network timeout")
        
        with pytest.raises(Exception, match="Osmosis API error"):
            billing_manager.swap_usdc_to_akt(
                usdc_amount=Decimal("100.0"),
                sender_address="osmo1test123"
            )
    
    def test_swap_usdc_to_akt_invalid_response(self, billing_manager, mock_requests_post):
        """Test handling of invalid response format"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "invalid_field": "missing_token_out_amount"
        }
        mock_requests_post.return_value = mock_response
        
        with pytest.raises(Exception, match="Invalid swap response"):
            billing_manager.swap_usdc_to_akt(
                usdc_amount=Decimal("100.0"),
                sender_address="osmo1test123"
            )
    
    def test_swap_usdc_to_akt_microunit_conversion(self, billing_manager, mock_requests_post):
        """Test proper microunit conversion for different amounts"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_out_amount": "95000000",  # 95 AKT
            "tx_hash": "0xmicrotest"
        }
        mock_requests_post.return_value = mock_response
        
        # Test with decimal USDC amount
        result = billing_manager.swap_usdc_to_akt(
            usdc_amount=Decimal("50.5"),
            sender_address="osmo1test123"
        )
        
        # Verify microunit conversion
        call_args = mock_requests_post.call_args
        swap_msg = call_args[1]["json"]["swap_exact_amount_in"]
        assert swap_msg["token_in"]["amount"] == "50500000"  # 50.5 USDC in microunits
        
        # Verify minimum output calculation
        expected_min_akt = Decimal("50.5") / Decimal("0.5") * Decimal("0.95")  # 95.95 AKT
        expected_min_microunits = str(int(expected_min_akt * 1_000_000))
        assert swap_msg["token_out_min_amount"] == expected_min_microunits
    
    def test_swap_usdc_to_akt_slippage_buffer(self, billing_manager, mock_requests_post):
        """Test that 5% slippage buffer is correctly applied"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_out_amount": "1900000000",  # 1900 AKT
            "tx_hash": "0xslippagetest"
        }
        mock_requests_post.return_value = mock_response
        
        result = billing_manager.swap_usdc_to_akt(
            usdc_amount=Decimal("1000.0"),
            sender_address="osmo1test123"
        )
        
        # Verify slippage buffer calculation
        expected_akt = Decimal("1000.0") / Decimal("0.5")  # 2000 AKT
        min_akt_with_slippage = expected_akt * Decimal("0.95")  # 1900 AKT
        
        assert result["min_akt_expected"] == str(min_akt_with_slippage)
        assert result["akt_received"] == "1900.0"
        assert result["slippage_used"] == "5.0"  # Exactly 5% slippage

if __name__ == "__main__":
    pytest.main([__file__])