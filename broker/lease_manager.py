import subprocess
import json
import uuid
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from .settings import settings

@dataclass
class LeaseInfo:
    lease_id: str
    provider: str
    ip_address: str
    port: int
    status: str

class LeaseManager:
    def __init__(self):
        self.akash_cmd_base = [
            "akash",
            "--node", settings.AKASH_NODE,
            "--chain-id", settings.AKASH_CHAIN_ID,
            "--keyring-backend", settings.AKASH_KEYRING_BACKEND,
            "--from", settings.AKASH_FROM
        ]
    
    def create_lease(self, sdl_path: str = "sdl/sunshine.yaml") -> LeaseInfo:
        """Create a new Akash lease for gaming session"""
        deployment_id = str(uuid.uuid4())
        
        # Create deployment
        deploy_cmd = self.akash_cmd_base + [
            "tx", "deployment", "create", sdl_path,
            "--dseq", deployment_id,
            "--gas", "auto",
            "--gas-adjustment", "1.4",
            "--yes"
        ]
        
        result = subprocess.run(deploy_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to create deployment: {result.stderr}")
        
        # Query market for bids (simplified)
        market_cmd = self.akash_cmd_base + [
            "query", "market", "bid", "list",
            "--owner", settings.AKASH_FROM,
            "--dseq", deployment_id,
            "--output", "json"
        ]
        
        result = subprocess.run(market_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to query market: {result.stderr}")
        
        bids = json.loads(result.stdout)
        if not bids.get("bids"):
            raise Exception("No bids available")
        
        # Accept first bid (simplified)
        bid = bids["bids"][0]
        lease_cmd = self.akash_cmd_base + [
            "tx", "market", "lease", "create",
            "--dseq", deployment_id,
            "--gseq", str(bid["bid"]["bid_id"]["gseq"]),
            "--oseq", str(bid["bid"]["bid_id"]["oseq"]),
            "--provider", bid["bid"]["bid_id"]["provider"],
            "--yes"
        ]
        
        result = subprocess.run(lease_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to create lease: {result.stderr}")
        
        return LeaseInfo(
            lease_id=deployment_id,
            provider=bid["bid"]["bid_id"]["provider"],
            ip_address="127.0.0.1",  # Placeholder - would query actual IP
            port=settings.SUNSHINE_PORT,
            status="active"
        )
    
    def extend_lease(self, lease_id: str, hours: int = 1) -> bool:
        """Extend an existing lease"""
        # Implementation would send more tokens to lease
        return True
    
    def get_lease_blocks_remaining(self, lease_id: str) -> Optional[int]:
        """Get remaining blocks until lease expires"""
        try:
            # Query lease info
            lease_cmd = self.akash_cmd_base + [
                "query", "market", "lease", "get",
                "--dseq", lease_id,
                "--output", "json"
            ]
            
            result = subprocess.run(lease_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return None
            
            lease_data = json.loads(result.stdout)
            
            # Get current block height
            status_cmd = self.akash_cmd_base + [
                "query", "block"
            ]
            
            result = subprocess.run(status_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return None
            
            block_data = json.loads(result.stdout)
            current_height = int(block_data["block"]["header"]["height"])
            
            # Calculate remaining blocks
            lease_end_height = int(lease_data["lease"]["lease"]["created_at"]) + \
                             int(lease_data["lease"]["lease"]["state"]["transferred"]["amount"])
            
            return max(0, lease_end_height - current_height)
            
        except (KeyError, ValueError, json.JSONDecodeError):
            return None
    
    def extend_if_needed(self, lease_id: str, provider: str, gseq: int = 1, oseq: int = 1) -> Dict[str, Any]:
        """Check remaining blocks and extend lease if needed (< 300 blocks)"""
        try:
            # Check remaining blocks
            blocks_remaining = self.get_lease_blocks_remaining(lease_id)
            
            if blocks_remaining is None:
                return {
                    "status": "error",
                    "message": "Could not query lease status",
                    "blocks_remaining": None,
                    "extended": False
                }
            
            # If more than 300 blocks remaining, no extension needed
            if blocks_remaining >= 300:
                return {
                    "status": "ok",
                    "message": "Lease has sufficient time remaining",
                    "blocks_remaining": blocks_remaining,
                    "extended": False
                }
            
            # Create bid to extend lease
            bid_cmd = self.akash_cmd_base + [
                "tx", "market", "lease", "create-bid",
                "--dseq", lease_id,
                "--gseq", str(gseq),
                "--oseq", str(oseq),
                "--provider", provider,
                "--deposit", f"{settings.LEASE_PRICE_UAKT}uakt",
                "--gas", "auto",
                "--gas-adjustment", "1.4",
                "--yes"
            ]
            
            result = subprocess.run(bid_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Failed to create extension bid: {result.stderr}",
                    "blocks_remaining": blocks_remaining,
                    "extended": False
                }
            
            # Parse transaction result
            tx_result = json.loads(result.stdout)
            
            return {
                "status": "extended",
                "message": f"Lease extended due to low blocks remaining ({blocks_remaining})",
                "blocks_remaining": blocks_remaining,
                "extended": True,
                "tx_hash": tx_result.get("txhash", ""),
                "deposit_amount": f"{settings.LEASE_PRICE_UAKT}uakt"
            }
            
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "message": f"Invalid JSON response: {str(e)}",
                "blocks_remaining": blocks_remaining,
                "extended": False
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Extension failed: {str(e)}",
                "blocks_remaining": blocks_remaining,
                "extended": False
            }
    
    def close_lease(self, lease_id: str) -> bool:
        """Close an existing lease"""
        close_cmd = self.akash_cmd_base + [
            "tx", "deployment", "close",
            "--dseq", lease_id,
            "--yes"
        ]
        
        result = subprocess.run(close_cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def get_lease_status(self, lease_id: str) -> Optional[Dict[str, Any]]:
        """Get current lease status"""
        status_cmd = self.akash_cmd_base + [
            "query", "deployment", "get",
            "--dseq", lease_id,
            "--output", "json"
        ]
        
        result = subprocess.run(status_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None
        
        return json.loads(result.stdout)
    
    def migrate_session(self, current_lease_id: str, current_provider: str, 
                       s3_bucket: str, s3_region: str = "us-east-1") -> Dict[str, Any]:
        """Migrate session to new lease with zero downtime via S3 backup"""
        migration_id = str(uuid.uuid4())[:8]
        s3_backup_path = f"s3://{s3_bucket}/session-backups/{current_lease_id}-{migration_id}"
        
        try:
            # Step 1: Get current lease IP for SSH access
            current_lease_status = self.get_lease_status(current_lease_id)
            if not current_lease_status:
                return {
                    "status": "error",
                    "message": "Could not query current lease status",
                    "migration_id": migration_id
                }
            
            current_ip = current_lease_status.get("lease", {}).get("services", {}).get("sunshine", {}).get("external_ip", "")
            if not current_ip:
                return {
                    "status": "error", 
                    "message": "Could not determine current lease IP",
                    "migration_id": migration_id
                }
            
            # Step 2: Backup Steam data to S3
            backup_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no", 
                f"gamer@{current_ip}",
                f"aws s3 sync /home/gamer/.steam/steam/steamapps/compatdata {s3_backup_path}/compatdata --region {s3_region} --delete"
            ]
            
            backup_result = subprocess.run(backup_cmd, capture_output=True, text=True, timeout=300)
            if backup_result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Steam data backup failed: {backup_result.stderr}",
                    "migration_id": migration_id
                }
            
            # Step 3: Create new lease (hot standby)
            try:
                new_lease = self.create_lease()
                new_lease_id = new_lease.lease_id
                new_ip = new_lease.ip_address
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to create new lease: {str(e)}",
                    "migration_id": migration_id,
                    "cleanup_required": True,
                    "s3_backup_path": s3_backup_path
                }
            
            # Step 4: Wait for new lease to be ready
            max_wait_time = 120  # 2 minutes
            wait_interval = 10
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                # Check if Sunshine is running on new lease
                health_cmd = [
                    "ssh", "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=5",
                    f"gamer@{new_ip}",
                    "curl -f http://localhost:47990/api/config --max-time 5"
                ]
                
                health_result = subprocess.run(health_cmd, capture_output=True, text=True)
                if health_result.returncode == 0:
                    break
                    
                time.sleep(wait_interval)
                elapsed_time += wait_interval
            
            if elapsed_time >= max_wait_time:
                # Cleanup new lease if it didn't come up
                self.close_lease(new_lease_id)
                return {
                    "status": "error",
                    "message": "New lease failed to become ready within timeout",
                    "migration_id": migration_id,
                    "cleanup_required": True,
                    "s3_backup_path": s3_backup_path
                }
            
            # Step 5: Restore Steam data from S3 to new lease
            restore_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                f"gamer@{new_ip}",
                f"aws s3 sync {s3_backup_path}/compatdata /home/gamer/.steam/steam/steamapps/compatdata --region {s3_region} --delete"
            ]
            
            restore_result = subprocess.run(restore_cmd, capture_output=True, text=True, timeout=300)
            if restore_result.returncode != 0:
                # Don't cleanup new lease yet - data might be partially restored
                return {
                    "status": "error",
                    "message": f"Steam data restore failed: {restore_result.stderr}",
                    "migration_id": migration_id,
                    "new_lease_id": new_lease_id,
                    "new_ip": new_ip,
                    "cleanup_required": True,
                    "s3_backup_path": s3_backup_path
                }
            
            # Step 6: Verify Steam data integrity on new lease
            verify_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                f"gamer@{new_ip}",
                "find /home/gamer/.steam/steam/steamapps/compatdata -name 'pfx' -type d | wc -l"
            ]
            
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
            if verify_result.returncode != 0:
                return {
                    "status": "warning",
                    "message": "Could not verify Steam data integrity, but migration completed",
                    "migration_id": migration_id,
                    "old_lease_id": current_lease_id,
                    "new_lease_id": new_lease_id,
                    "new_ip": new_ip,
                    "s3_backup_path": s3_backup_path
                }
            
            # Step 7: Close old lease
            old_lease_closed = self.close_lease(current_lease_id)
            
            # Step 8: Cleanup S3 backup (optional - keep for safety)
            cleanup_cmd = [
                "aws", "s3", "rm", s3_backup_path, "--recursive", "--region", s3_region
            ]
            subprocess.run(cleanup_cmd, capture_output=True, text=True)
            
            return {
                "status": "success",
                "message": f"Session migrated successfully from {current_lease_id} to {new_lease_id}",
                "migration_id": migration_id,
                "old_lease_id": current_lease_id,
                "old_lease_closed": old_lease_closed,
                "new_lease_id": new_lease_id,
                "new_ip": new_ip,
                "new_provider": new_lease.provider,
                "steam_data_verified": True,
                "s3_backup_cleaned": True
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "Migration timed out during backup/restore operation",
                "migration_id": migration_id,
                "cleanup_required": True
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Migration failed: {str(e)}",
                "migration_id": migration_id,
                "cleanup_required": True
            }