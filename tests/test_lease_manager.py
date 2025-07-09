import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from broker.lease_manager import LeaseManager, LeaseInfo
from broker.settings import settings

class TestLeaseManager:
    
    @pytest.fixture
    def lease_manager(self):
        return LeaseManager()
    
    @pytest.fixture
    def mock_subprocess_run(self):
        with patch('broker.lease_manager.subprocess.run') as mock_run:
            yield mock_run
    
    def test_init_sets_correct_command_base(self, lease_manager):
        """Test that LeaseManager initializes with correct Akash command base"""
        expected_base = [
            "akash",
            "--node", settings.AKASH_NODE,
            "--chain-id", settings.AKASH_CHAIN_ID,
            "--keyring-backend", settings.AKASH_KEYRING_BACKEND,
            "--from", settings.AKASH_FROM
        ]
        assert lease_manager.akash_cmd_base == expected_base
    
    def test_create_lease_success(self, lease_manager, mock_subprocess_run):
        """Test successful lease creation"""
        # Mock deployment creation
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # create deployment
            Mock(returncode=0, stdout=json.dumps({
                "bids": [{
                    "bid": {
                        "bid_id": {
                            "provider": "akash1test",
                            "gseq": 1,
                            "oseq": 1
                        }
                    }
                }]
            }), stderr=""),  # query market
            Mock(returncode=0, stdout="", stderr="")  # create lease
        ]
        
        result = lease_manager.create_lease()
        
        assert isinstance(result, LeaseInfo)
        assert result.provider == "akash1test"
        assert result.ip_address == "127.0.0.1"
        assert result.port == settings.SUNSHINE_PORT
        assert result.status == "active"
        assert mock_subprocess_run.call_count == 3
    
    def test_create_lease_deployment_fails(self, lease_manager, mock_subprocess_run):
        """Test lease creation failure during deployment"""
        mock_subprocess_run.return_value = Mock(
            returncode=1, 
            stdout="", 
            stderr="deployment failed"
        )
        
        with pytest.raises(Exception, match="Failed to create deployment"):
            lease_manager.create_lease()
    
    def test_create_lease_no_bids(self, lease_manager, mock_subprocess_run):
        """Test lease creation failure when no bids are available"""
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # create deployment
            Mock(returncode=0, stdout=json.dumps({"bids": []}), stderr="")  # no bids
        ]
        
        with pytest.raises(Exception, match="No bids available"):
            lease_manager.create_lease()
    
    def test_create_lease_market_query_fails(self, lease_manager, mock_subprocess_run):
        """Test lease creation failure during market query"""
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # create deployment
            Mock(returncode=1, stdout="", stderr="market query failed")  # query fails
        ]
        
        with pytest.raises(Exception, match="Failed to query market"):
            lease_manager.create_lease()
    
    def test_create_lease_lease_creation_fails(self, lease_manager, mock_subprocess_run):
        """Test lease creation failure during lease creation"""
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # create deployment
            Mock(returncode=0, stdout=json.dumps({
                "bids": [{
                    "bid": {
                        "bid_id": {
                            "provider": "akash1test",
                            "gseq": 1,
                            "oseq": 1
                        }
                    }
                }]
            }), stderr=""),  # query market
            Mock(returncode=1, stdout="", stderr="lease creation failed")  # lease fails
        ]
        
        with pytest.raises(Exception, match="Failed to create lease"):
            lease_manager.create_lease()
    
    def test_extend_lease_success(self, lease_manager):
        """Test successful lease extension"""
        result = lease_manager.extend_lease("test-lease-id", 2)
        assert result is True
    
    def test_close_lease_success(self, lease_manager, mock_subprocess_run):
        """Test successful lease closure"""
        mock_subprocess_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        result = lease_manager.close_lease("test-lease-id")
        
        assert result is True
        mock_subprocess_run.assert_called_once()
        
        # Verify correct command was called
        called_args = mock_subprocess_run.call_args[0][0]
        assert "tx" in called_args
        assert "deployment" in called_args
        assert "close" in called_args
        assert "test-lease-id" in called_args
    
    def test_close_lease_failure(self, lease_manager, mock_subprocess_run):
        """Test lease closure failure"""
        mock_subprocess_run.return_value = Mock(returncode=1, stdout="", stderr="")
        
        result = lease_manager.close_lease("test-lease-id")
        
        assert result is False
    
    def test_get_lease_status_success(self, lease_manager, mock_subprocess_run):
        """Test successful lease status retrieval"""
        status_data = {"deployment": {"state": "active"}}
        mock_subprocess_run.return_value = Mock(
            returncode=0, 
            stdout=json.dumps(status_data), 
            stderr=""
        )
        
        result = lease_manager.get_lease_status("test-lease-id")
        
        assert result == status_data
        mock_subprocess_run.assert_called_once()
    
    def test_get_lease_status_failure(self, lease_manager, mock_subprocess_run):
        """Test lease status retrieval failure"""
        mock_subprocess_run.return_value = Mock(returncode=1, stdout="", stderr="")
        
        result = lease_manager.get_lease_status("test-lease-id")
        
        assert result is None
    
    def test_get_lease_status_invalid_json(self, lease_manager, mock_subprocess_run):
        """Test lease status retrieval with invalid JSON"""
        mock_subprocess_run.return_value = Mock(
            returncode=0, 
            stdout="invalid json", 
            stderr=""
        )
        
        with pytest.raises(json.JSONDecodeError):
            lease_manager.get_lease_status("test-lease-id")
    
    def test_get_lease_blocks_remaining_success(self, lease_manager, mock_subprocess_run):
        """Test successful blocks remaining calculation"""
        # Mock lease query response
        lease_data = {
            "lease": {
                "lease": {
                    "created_at": "1000",
                    "state": {
                        "transferred": {
                            "amount": "500"
                        }
                    }
                }
            }
        }
        
        # Mock block query response
        block_data = {
            "block": {
                "header": {
                    "height": "1200"
                }
            }
        }
        
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout=json.dumps(lease_data), stderr=""),
            Mock(returncode=0, stdout=json.dumps(block_data), stderr="")
        ]
        
        result = lease_manager.get_lease_blocks_remaining("test-lease-id")
        
        # Expected: lease_end_height (1000 + 500) - current_height (1200) = 300
        assert result == 300
    
    def test_get_lease_blocks_remaining_expired(self, lease_manager, mock_subprocess_run):
        """Test when lease has already expired"""
        lease_data = {
            "lease": {
                "lease": {
                    "created_at": "1000",
                    "state": {
                        "transferred": {
                            "amount": "200"
                        }
                    }
                }
            }
        }
        
        block_data = {
            "block": {
                "header": {
                    "height": "1500"
                }
            }
        }
        
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout=json.dumps(lease_data), stderr=""),
            Mock(returncode=0, stdout=json.dumps(block_data), stderr="")
        ]
        
        result = lease_manager.get_lease_blocks_remaining("test-lease-id")
        
        # Expected: max(0, 1200 - 1500) = 0
        assert result == 0
    
    def test_get_lease_blocks_remaining_failure(self, lease_manager, mock_subprocess_run):
        """Test when lease query fails"""
        mock_subprocess_run.return_value = Mock(returncode=1, stdout="", stderr="error")
        
        result = lease_manager.get_lease_blocks_remaining("test-lease-id")
        
        assert result is None
    
    def test_extend_if_needed_sufficient_blocks(self, lease_manager, mock_subprocess_run):
        """Test when lease has sufficient blocks remaining"""
        # Mock blocks remaining check
        lease_data = {
            "lease": {
                "lease": {
                    "created_at": "1000",
                    "state": {
                        "transferred": {
                            "amount": "800"
                        }
                    }
                }
            }
        }
        
        block_data = {
            "block": {
                "header": {
                    "height": "1200"
                }
            }
        }
        
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout=json.dumps(lease_data), stderr=""),
            Mock(returncode=0, stdout=json.dumps(block_data), stderr="")
        ]
        
        result = lease_manager.extend_if_needed("test-lease-id", "test-provider")
        
        # Expected: 600 blocks remaining (> 300), no extension needed
        assert result["status"] == "ok"
        assert result["blocks_remaining"] == 600
        assert result["extended"] is False
        assert "sufficient time remaining" in result["message"]
    
    def test_extend_if_needed_extension_required(self, lease_manager, mock_subprocess_run):
        """Test when lease needs extension due to low blocks"""
        # Mock blocks remaining check (< 300)
        lease_data = {
            "lease": {
                "lease": {
                    "created_at": "1000",
                    "state": {
                        "transferred": {
                            "amount": "200"
                        }
                    }
                }
            }
        }
        
        block_data = {
            "block": {
                "header": {
                    "height": "1050"
                }
            }
        }
        
        # Mock successful extension
        tx_result = {
            "txhash": "0xABC123DEF456"
        }
        
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout=json.dumps(lease_data), stderr=""),
            Mock(returncode=0, stdout=json.dumps(block_data), stderr=""),
            Mock(returncode=0, stdout=json.dumps(tx_result), stderr="")
        ]
        
        result = lease_manager.extend_if_needed("test-lease-id", "test-provider")
        
        # Expected: 150 blocks remaining (< 300), extension created
        assert result["status"] == "extended"
        assert result["blocks_remaining"] == 150
        assert result["extended"] is True
        assert result["tx_hash"] == "0xABC123DEF456"
        assert result["deposit_amount"] == f"{settings.LEASE_PRICE_UAKT}uakt"
    
    def test_extend_if_needed_extension_fails(self, lease_manager, mock_subprocess_run):
        """Test when extension bid creation fails"""
        # Mock blocks remaining check (< 300)
        lease_data = {
            "lease": {
                "lease": {
                    "created_at": "1000",
                    "state": {
                        "transferred": {
                            "amount": "100"
                        }
                    }
                }
            }
        }
        
        block_data = {
            "block": {
                "header": {
                    "height": "1050"
                }
            }
        }
        
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout=json.dumps(lease_data), stderr=""),
            Mock(returncode=0, stdout=json.dumps(block_data), stderr=""),
            Mock(returncode=1, stdout="", stderr="bid creation failed")
        ]
        
        result = lease_manager.extend_if_needed("test-lease-id", "test-provider")
        
        assert result["status"] == "error"
        assert result["blocks_remaining"] == 50
        assert result["extended"] is False
        assert "Failed to create extension bid" in result["message"]
    
    def test_extend_if_needed_query_fails(self, lease_manager, mock_subprocess_run):
        """Test when lease status query fails"""
        mock_subprocess_run.return_value = Mock(returncode=1, stdout="", stderr="query failed")
        
        result = lease_manager.extend_if_needed("test-lease-id", "test-provider")
        
        assert result["status"] == "error"
        assert result["blocks_remaining"] is None
        assert result["extended"] is False
        assert "Could not query lease status" in result["message"]
    
    def test_extend_if_needed_with_custom_params(self, lease_manager, mock_subprocess_run):
        """Test extension with custom gseq and oseq parameters"""
        # Mock blocks remaining check (< 300)
        lease_data = {
            "lease": {
                "lease": {
                    "created_at": "1000",
                    "state": {
                        "transferred": {
                            "amount": "100"
                        }
                    }
                }
            }
        }
        
        block_data = {
            "block": {
                "header": {
                    "height": "1050"
                }
            }
        }
        
        tx_result = {"txhash": "0xCUSTOM123"}
        
        mock_subprocess_run.side_effect = [
            Mock(returncode=0, stdout=json.dumps(lease_data), stderr=""),
            Mock(returncode=0, stdout=json.dumps(block_data), stderr=""),
            Mock(returncode=0, stdout=json.dumps(tx_result), stderr="")
        ]
        
        result = lease_manager.extend_if_needed("test-lease-id", "test-provider", gseq=2, oseq=3)
        
        # Verify custom parameters were used in the command
        assert result["status"] == "extended"
        
        # Check that the bid command was called with correct parameters
        bid_call_args = mock_subprocess_run.call_args_list[2][0][0]
        assert "--gseq" in bid_call_args
        assert "2" in bid_call_args
        assert "--oseq" in bid_call_args
        assert "3" in bid_call_args
    
    @patch('broker.lease_manager.time.sleep')
    def test_migrate_session_success(self, mock_sleep, lease_manager, mock_subprocess_run):
        """Test successful session migration"""
        # Mock current lease status
        current_lease_status = {
            "lease": {
                "services": {
                    "sunshine": {
                        "external_ip": "192.168.1.100"
                    }
                }
            }
        }
        
        # Mock new lease creation
        new_lease = LeaseInfo(
            lease_id="new-lease-123",
            provider="new-provider",
            ip_address="192.168.1.200",
            port=47984,
            status="active"
        )
        
        # Mock all subprocess calls
        mock_subprocess_run.side_effect = [
            # get_lease_status call
            Mock(returncode=0, stdout=json.dumps(current_lease_status), stderr=""),
            # S3 backup
            Mock(returncode=0, stdout="backup complete", stderr=""),
            # Health check (new lease ready)
            Mock(returncode=0, stdout="healthy", stderr=""),
            # S3 restore
            Mock(returncode=0, stdout="restore complete", stderr=""),
            # Data integrity verification
            Mock(returncode=0, stdout="5", stderr=""),
            # Close old lease
            Mock(returncode=0, stdout="", stderr=""),
            # S3 cleanup
            Mock(returncode=0, stdout="", stderr="")
        ]
        
        # Mock create_lease
        with patch.object(lease_manager, 'create_lease', return_value=new_lease):
            with patch.object(lease_manager, 'close_lease', return_value=True):
                result = lease_manager.migrate_session(
                    current_lease_id="old-lease-123",
                    current_provider="old-provider", 
                    s3_bucket="gaming-backups"
                )
        
        # Verify successful migration
        assert result["status"] == "success"
        assert result["old_lease_id"] == "old-lease-123"
        assert result["new_lease_id"] == "new-lease-123"
        assert result["new_ip"] == "192.168.1.200"
        assert result["steam_data_verified"] is True
        assert result["s3_backup_cleaned"] is True
        
        # Verify S3 backup command was called
        backup_call = mock_subprocess_run.call_args_list[1]
        assert "aws s3 sync" in " ".join(backup_call[0][0])
        assert "/home/gamer/.steam/steam/steamapps/compatdata" in " ".join(backup_call[0][0])
        assert "gaming-backups" in " ".join(backup_call[0][0])
    
    def test_migrate_session_backup_failure(self, lease_manager, mock_subprocess_run):
        """Test migration failure during S3 backup"""
        current_lease_status = {
            "lease": {
                "services": {
                    "sunshine": {
                        "external_ip": "192.168.1.100"
                    }
                }
            }
        }
        
        mock_subprocess_run.side_effect = [
            # get_lease_status call
            Mock(returncode=0, stdout=json.dumps(current_lease_status), stderr=""),
            # S3 backup failure
            Mock(returncode=1, stdout="", stderr="S3 access denied")
        ]
        
        result = lease_manager.migrate_session(
            current_lease_id="old-lease-123",
            current_provider="old-provider",
            s3_bucket="gaming-backups"
        )
        
        assert result["status"] == "error"
        assert "Steam data backup failed" in result["message"]
        assert "S3 access denied" in result["message"]
    
    @patch('broker.lease_manager.time.sleep')
    def test_migrate_session_new_lease_timeout(self, mock_sleep, lease_manager, mock_subprocess_run):
        """Test migration failure when new lease doesn't become ready"""
        current_lease_status = {
            "lease": {
                "services": {
                    "sunshine": {
                        "external_ip": "192.168.1.100"
                    }
                }
            }
        }
        
        new_lease = LeaseInfo(
            lease_id="new-lease-123",
            provider="new-provider",
            ip_address="192.168.1.200",
            port=47984,
            status="active"
        )
        
        mock_subprocess_run.side_effect = [
            # get_lease_status call
            Mock(returncode=0, stdout=json.dumps(current_lease_status), stderr=""),
            # S3 backup
            Mock(returncode=0, stdout="backup complete", stderr=""),
            # Health check failures (simulate timeout)
            Mock(returncode=1, stdout="", stderr="connection refused"),
            Mock(returncode=1, stdout="", stderr="connection refused"),
            # close_lease call for cleanup
            Mock(returncode=0, stdout="", stderr="")
        ]
        
        with patch.object(lease_manager, 'create_lease', return_value=new_lease):
            with patch.object(lease_manager, 'close_lease', return_value=True):
                result = lease_manager.migrate_session(
                    current_lease_id="old-lease-123",
                    current_provider="old-provider",
                    s3_bucket="gaming-backups"
                )
        
        assert result["status"] == "error"
        assert "New lease failed to become ready within timeout" in result["message"]
        assert result["cleanup_required"] is True
    
    def test_migrate_session_restore_failure(self, lease_manager, mock_subprocess_run):
        """Test migration failure during S3 restore"""
        current_lease_status = {
            "lease": {
                "services": {
                    "sunshine": {
                        "external_ip": "192.168.1.100"
                    }
                }
            }
        }
        
        new_lease = LeaseInfo(
            lease_id="new-lease-123",
            provider="new-provider",
            ip_address="192.168.1.200",
            port=47984,
            status="active"
        )
        
        mock_subprocess_run.side_effect = [
            # get_lease_status call
            Mock(returncode=0, stdout=json.dumps(current_lease_status), stderr=""),
            # S3 backup
            Mock(returncode=0, stdout="backup complete", stderr=""),
            # Health check (new lease ready)
            Mock(returncode=0, stdout="healthy", stderr=""),
            # S3 restore failure
            Mock(returncode=1, stdout="", stderr="S3 restore failed")
        ]
        
        with patch.object(lease_manager, 'create_lease', return_value=new_lease):
            result = lease_manager.migrate_session(
                current_lease_id="old-lease-123",
                current_provider="old-provider",
                s3_bucket="gaming-backups"
            )
        
        assert result["status"] == "error"
        assert "Steam data restore failed" in result["message"]
        assert result["new_lease_id"] == "new-lease-123"
        assert result["cleanup_required"] is True
    
    def test_migrate_session_no_current_lease(self, lease_manager, mock_subprocess_run):
        """Test migration failure when current lease cannot be queried"""
        mock_subprocess_run.return_value = Mock(returncode=1, stdout="", stderr="lease not found")
        
        with patch.object(lease_manager, 'get_lease_status', return_value=None):
            result = lease_manager.migrate_session(
                current_lease_id="nonexistent-lease",
                current_provider="old-provider",
                s3_bucket="gaming-backups"
            )
        
        assert result["status"] == "error"
        assert "Could not query current lease status" in result["message"]
    
    def test_migrate_session_no_current_ip(self, lease_manager, mock_subprocess_run):
        """Test migration failure when current lease IP cannot be determined"""
        # Mock lease status without external IP
        current_lease_status = {
            "lease": {
                "services": {
                    "sunshine": {}
                }
            }
        }
        
        with patch.object(lease_manager, 'get_lease_status', return_value=current_lease_status):
            result = lease_manager.migrate_session(
                current_lease_id="old-lease-123",
                current_provider="old-provider",
                s3_bucket="gaming-backups"
            )
        
        assert result["status"] == "error"
        assert "Could not determine current lease IP" in result["message"]

if __name__ == "__main__":
    pytest.main([__file__])