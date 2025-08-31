"""
Unit tests for Multi-Factor Identity Verification system.

Tests comprehensive identity verification including:
- Email token generation and verification
- Knowledge-based authentication
- Risk assessment and scoring
- Multi-factor verification coordination
- Rate limiting and fraud protection
- Account lockout mechanisms
- Security token handling
- Audit logging of verification attempts
"""

import pytest
import asyncio
import secrets
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from devdocai.dsr.identity.verifier import (
    IdentityVerifier, VerificationToken, RiskAssessment, VerificationAttempt,
    VerificationMethod, VerificationStatus, RiskLevel
)
from devdocai.core.config import ConfigurationManager


@pytest.fixture
async def config_manager():
    """Mock configuration manager for testing."""
    config = Mock(spec=ConfigurationManager)
    config.get_encryption_key = Mock(return_value="test_identity_key_32_bytes_long!")
    return config


@pytest.fixture
async def identity_verifier(config_manager):
    """Initialize Identity Verifier for testing."""
    verifier = IdentityVerifier(config_manager)
    return verifier


@pytest.fixture
def sample_verification_context():
    """Sample verification context for testing."""
    return {
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Test Browser)",
        "geolocation": "US",
        "device_fingerprint": "test_device_123"
    }


class TestVerificationToken:
    """Test verification token functionality."""
    
    def test_token_creation(self):
        """Test secure token creation."""
        token = VerificationToken(
            user_id="test_user",
            email="test@example.com"
        )
        
        assert token.user_id == "test_user"
        assert token.email == "test@example.com"
        assert len(token.token) == 6  # 6-digit token
        assert token.token.isdigit()  # Should be numeric
        assert len(token.token_hash) == 64  # SHA-256 hex
        assert token.created_at <= datetime.utcnow()
        assert token.expires_at > datetime.utcnow()
        assert token.attempts == 0
        assert token.max_attempts == 3
    
    def test_token_validity_check(self):
        """Test token validity checking."""
        token = VerificationToken(user_id="test", email="test@test.com")
        
        # Fresh token should be valid
        assert token.is_valid()
        
        # Expired token should be invalid
        token.expires_at = datetime.utcnow() - timedelta(minutes=1)
        assert not token.is_valid()
        
        # Token with max attempts should be invalid
        token.expires_at = datetime.utcnow() + timedelta(minutes=10)
        token.attempts = token.max_attempts
        assert not token.is_valid()
    
    def test_token_verification(self):
        """Test token verification with correct and incorrect tokens."""
        token = VerificationToken(user_id="test", email="test@test.com")
        correct_token = token.token
        
        # Correct token should verify successfully
        assert token.verify_token(correct_token)
        assert token.attempts == 1
        
        # Incorrect token should fail
        assert not token.verify_token("000000")
        assert token.attempts == 2
        
        # Another incorrect token
        assert not token.verify_token("999999")
        assert token.attempts == 3
        
        # Token should now be invalid due to max attempts
        assert not token.is_valid()
        assert not token.verify_token(correct_token)  # Even correct token fails
    
    def test_token_security_features(self):
        """Test token security features."""
        token = VerificationToken(user_id="test", email="test@test.com")
        
        # Token should be cryptographically random (basic check)
        tokens = set()
        for _ in range(10):
            new_token = VerificationToken(user_id="test", email="test@test.com")
            tokens.add(new_token.token)
        
        # All tokens should be unique (very high probability)
        assert len(tokens) == 10
        
        # Hash should be deterministic for same token
        test_token = "123456"
        hash1 = token._hash_token(test_token)
        hash2 = token._hash_token(test_token)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex


class TestRiskAssessment:
    """Test risk assessment functionality."""
    
    def test_risk_assessment_creation(self):
        """Test risk assessment initialization."""
        assessment = RiskAssessment(user_id="test_user")
        
        assert assessment.user_id == "test_user"
        assert assessment.risk_score == 0.0
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.risk_factors == []
        assert assessment.geolocation_check is True
        assert assessment.access_pattern_anomaly is False
    
    def test_risk_score_calculation_low_risk(self):
        """Test risk score calculation for low-risk scenario.""" 
        assessment = RiskAssessment(user_id="safe_user")
        assessment.geolocation_check = True
        assessment.device_fingerprint = "known_device_123"
        assessment.access_pattern_anomaly = False
        assessment.previous_breach_indicator = False
        
        score = assessment.calculate_risk_score()
        
        assert score == 0.0
        assert assessment.risk_level == RiskLevel.LOW
        assert len(assessment.risk_factors) == 0
    
    def test_risk_score_calculation_high_risk(self):
        """Test risk score calculation for high-risk scenario."""
        assessment = RiskAssessment(user_id="risky_user")
        assessment.geolocation_check = False  # +0.3
        assessment.device_fingerprint = ""    # +0.2  
        assessment.access_pattern_anomaly = True  # +0.4
        assessment.previous_breach_indicator = False
        
        score = assessment.calculate_risk_score()
        
        assert score == 0.9  # 0.3 + 0.2 + 0.4
        assert assessment.risk_level == RiskLevel.CRITICAL
        assert "unusual_location" in assessment.risk_factors
        assert "unknown_device" in assessment.risk_factors
        assert "unusual_access_pattern" in assessment.risk_factors
    
    def test_risk_level_thresholds(self):
        """Test risk level threshold calculations."""
        assessment = RiskAssessment(user_id="test")
        
        # Low risk (0.0 - 0.29)
        assessment.risk_score = 0.2
        assessment.calculate_risk_score()
        assert assessment.risk_level == RiskLevel.LOW
        
        # Medium risk (0.3 - 0.59)  
        assessment.risk_score = 0.4
        assessment.calculate_risk_score()
        assert assessment.risk_level == RiskLevel.MEDIUM
        
        # High risk (0.6 - 0.79)
        assessment.risk_score = 0.7
        assessment.calculate_risk_score()
        assert assessment.risk_level == RiskLevel.HIGH
        
        # Critical risk (0.8+)
        assessment.risk_score = 0.9
        assessment.calculate_risk_score()
        assert assessment.risk_level == RiskLevel.CRITICAL


class TestIdentityVerifierCore:
    """Test core Identity Verifier functionality."""
    
    @pytest.mark.asyncio
    async def test_verifier_initialization(self, config_manager):
        """Test Identity Verifier initialization."""
        verifier = IdentityVerifier(config_manager)
        
        assert verifier.config_manager == config_manager
        assert verifier.active_tokens == {}
        assert verifier.verification_attempts == []
        assert verifier.rate_limit_tracking == {}
        assert verifier.max_attempts_per_hour == 5
        assert verifier.lockout_duration_minutes == 30
        assert verifier.token_expiry_minutes == 15
        assert verifier.cipher_suite is not None  # Encryption initialized
    
    @pytest.mark.asyncio
    async def test_verification_initiation_success(self, identity_verifier, sample_verification_context):
        """Test successful verification initiation."""
        result = await identity_verifier.initiate_verification(
            user_id="test_user_123",
            email="test@example.com",
            ip_address=sample_verification_context["ip_address"],
            user_agent=sample_verification_context["user_agent"]
        )
        
        assert result["success"] is True
        assert result["verification_id"] == "test_user_123"
        assert "email_token" in result["methods_required"]
        assert result["risk_level"] == "low"  # Default risk
        assert result["token_expires_in_minutes"] == 15
        
        # Verify token was created and stored
        assert "test_user_123" in identity_verifier.active_tokens
        token = identity_verifier.active_tokens["test_user_123"]
        assert token.user_id == "test_user_123"
        assert token.email == "test@example.com"
        
        # Verify verification attempt was logged
        assert len(identity_verifier.verification_attempts) == 1
        attempt = identity_verifier.verification_attempts[0]
        assert attempt.user_id == "test_user_123"
        assert attempt.method == VerificationMethod.EMAIL_TOKEN
        assert attempt.status == VerificationStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_email_token_verification_success(self, identity_verifier):
        """Test successful email token verification."""
        # First initiate verification
        await identity_verifier.initiate_verification(
            user_id="token_user",
            email="token@test.com"
        )
        
        # Get the generated token
        token = identity_verifier.active_tokens["token_user"]
        correct_token = token.token
        
        # Verify the token
        result = await identity_verifier.verify_email_token("token_user", correct_token)
        
        assert result["success"] is True
        assert result["status"] == VerificationStatus.SUCCESS.value
        assert result["method"] == VerificationMethod.EMAIL_TOKEN.value
        
        # Verify attempt was logged
        success_attempts = [
            a for a in identity_verifier.verification_attempts
            if a.status == VerificationStatus.SUCCESS
        ]
        assert len(success_attempts) == 1
    
    @pytest.mark.asyncio
    async def test_email_token_verification_failure(self, identity_verifier):
        """Test email token verification failure."""
        # Initiate verification
        await identity_verifier.initiate_verification(
            user_id="fail_user",
            email="fail@test.com"
        )
        
        # Try incorrect token
        result = await identity_verifier.verify_email_token("fail_user", "000000")
        
        assert result["success"] is False
        assert result["status"] == VerificationStatus.FAILED.value
        assert "2 attempts remaining" in result["message"]
        
        # Token should still exist with incremented attempts
        token = identity_verifier.active_tokens["fail_user"]
        assert token.attempts == 1
    
    @pytest.mark.asyncio
    async def test_email_token_max_attempts(self, identity_verifier):
        """Test email token maximum attempts handling."""
        await identity_verifier.initiate_verification(
            user_id="max_attempts_user",
            email="max@test.com"
        )
        
        # Use up all attempts with wrong tokens
        for i in range(3):
            result = await identity_verifier.verify_email_token("max_attempts_user", "000000")
            assert result["success"] is False
        
        # After 3 attempts, token should be removed
        final_result = await identity_verifier.verify_email_token("max_attempts_user", "000000")
        assert "Maximum token attempts reached" in final_result["message"]
        assert "max_attempts_user" not in identity_verifier.active_tokens
    
    @pytest.mark.asyncio
    async def test_knowledge_based_verification(self, identity_verifier):
        """Test knowledge-based authentication."""
        answers = {
            "account_email": "user@example.com",
            "recent_document": "My Latest Document",
            "configuration_theme": "dark"
        }
        
        result = await identity_verifier.verify_knowledge_based("kb_user", answers)
        
        assert result["success"] is True
        assert result["method"] == VerificationMethod.KNOWLEDGE_BASED.value
        
        # Verify attempt was logged with details
        kb_attempts = [
            a for a in identity_verifier.verification_attempts
            if a.method == VerificationMethod.KNOWLEDGE_BASED
        ]
        assert len(kb_attempts) == 1
        assert kb_attempts[0].details["questions_answered"] == 3


class TestRateLimitingAndSecurity:
    """Test rate limiting and security features."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_check(self, identity_verifier):
        """Test rate limiting functionality."""
        user_id = "rate_limited_user"
        
        # Should not be rate limited initially
        assert not await identity_verifier._is_rate_limited(user_id)
        
        # Simulate 5 attempts in the last hour
        current_time = time.time()
        identity_verifier.rate_limit_tracking[user_id] = [
            current_time - 1800,  # 30 minutes ago
            current_time - 1200,  # 20 minutes ago  
            current_time - 600,   # 10 minutes ago
            current_time - 300,   # 5 minutes ago
            current_time - 60     # 1 minute ago
        ]
        
        # Should now be rate limited
        assert await identity_verifier._is_rate_limited(user_id)
    
    @pytest.mark.asyncio
    async def test_user_lockout_mechanism(self, identity_verifier):
        """Test user lockout after failed attempts."""
        user_id = "lockout_user"
        
        # Should not be locked initially
        assert not await identity_verifier._is_user_locked(user_id)
        
        # Record multiple failed attempts
        for _ in range(5):
            await identity_verifier._record_failed_attempt(user_id)
        
        # User should now be locked
        assert await identity_verifier._is_user_locked(user_id)
        assert user_id in identity_verifier.locked_users
        
        # Get remaining lockout time
        remaining = identity_verifier._get_lockout_remaining_minutes(user_id)
        assert remaining > 0
        assert remaining <= 30  # Max lockout duration
    
    @pytest.mark.asyncio
    async def test_verification_with_lockout(self, identity_verifier):
        """Test verification attempt while user is locked out."""
        user_id = "locked_user"
        
        # Lock the user
        await identity_verifier._record_failed_attempt(user_id)
        await identity_verifier._record_failed_attempt(user_id) 
        await identity_verifier._record_failed_attempt(user_id)
        await identity_verifier._record_failed_attempt(user_id)
        await identity_verifier._record_failed_attempt(user_id)
        
        # Try to initiate verification
        result = await identity_verifier.initiate_verification(
            user_id=user_id,
            email="locked@test.com"
        )
        
        assert result["success"] is False
        assert result["status"] == VerificationStatus.LOCKED.value
        assert "temporarily locked" in result["message"]
        assert "retry_after_minutes" in result
    
    @pytest.mark.asyncio
    async def test_verification_with_rate_limiting(self, identity_verifier):
        """Test verification attempt while rate limited."""
        user_id = "rate_user"
        
        # Simulate rate limiting
        current_time = time.time()
        identity_verifier.rate_limit_tracking[user_id] = [current_time] * 5
        
        result = await identity_verifier.initiate_verification(
            user_id=user_id,
            email="rate@test.com"
        )
        
        assert result["success"] is False
        assert result["status"] == VerificationStatus.RATE_LIMITED.value
        assert "Too many verification attempts" in result["message"]


class TestMultiFactorVerificationWorkflow:
    """Test complete multi-factor verification workflow."""
    
    @pytest.mark.asyncio
    async def test_single_factor_verification_completion(self, identity_verifier):
        """Test completion with single factor (email token only)."""
        user_id = "single_factor_user"
        
        # Initiate verification
        await identity_verifier.initiate_verification(
            user_id=user_id,
            email="single@test.com"
        )
        
        # Complete email verification
        token = identity_verifier.active_tokens[user_id]
        await identity_verifier.verify_email_token(user_id, token.token)
        
        # Complete verification
        result = await identity_verifier.complete_verification(
            user_id=user_id,
            completed_methods=[VerificationMethod.EMAIL_TOKEN]
        )
        
        assert result["success"] is True
        assert result["verification_complete"] is True
        assert VerificationMethod.EMAIL_TOKEN.value in result["methods_completed"]
        assert result["verification_level"] == "standard"
        
        # Token should be cleaned up
        assert user_id not in identity_verifier.active_tokens
    
    @pytest.mark.asyncio
    async def test_multi_factor_verification_completion(self, identity_verifier):
        """Test completion with multiple factors (email + knowledge-based)."""
        user_id = "multi_factor_user"
        
        # Enable knowledge-based requirement
        identity_verifier.require_knowledge_auth = True
        
        # Initiate verification with high risk
        with patch.object(identity_verifier, '_assess_risk') as mock_risk:
            mock_assessment = RiskAssessment(user_id=user_id)
            mock_assessment.risk_score = 0.7  # High risk
            mock_assessment.risk_level = RiskLevel.HIGH
            mock_risk.return_value = mock_assessment
            
            await identity_verifier.initiate_verification(
                user_id=user_id,
                email="multi@test.com"
            )
        
        # Complete email verification
        token = identity_verifier.active_tokens[user_id]
        await identity_verifier.verify_email_token(user_id, token.token)
        
        # Complete knowledge-based verification
        await identity_verifier.verify_knowledge_based(user_id, {
            "account_email": "multi@test.com",
            "recent_document": "Test Doc",
            "configuration_theme": "light"
        })
        
        # Complete verification
        result = await identity_verifier.complete_verification(
            user_id=user_id,
            completed_methods=[VerificationMethod.EMAIL_TOKEN, VerificationMethod.KNOWLEDGE_BASED]
        )
        
        assert result["success"] is True
        assert result["verification_complete"] is True
        assert len(result["methods_completed"]) == 2
        assert result["verification_level"] == "high"
        assert result["final_risk_score"] == 0.7
    
    @pytest.mark.asyncio
    async def test_incomplete_verification(self, identity_verifier):
        """Test incomplete verification (missing required methods)."""
        user_id = "incomplete_user"
        
        # Enable knowledge-based requirement
        identity_verifier.require_knowledge_auth = True
        
        await identity_verifier.initiate_verification(
            user_id=user_id,
            email="incomplete@test.com"
        )
        
        # Only complete email verification (missing knowledge-based)
        token = identity_verifier.active_tokens[user_id]
        await identity_verifier.verify_email_token(user_id, token.token)
        
        # Try to complete verification
        result = await identity_verifier.complete_verification(
            user_id=user_id,
            completed_methods=[VerificationMethod.EMAIL_TOKEN]
        )
        
        assert result["success"] is False
        assert result["verification_complete"] is False
        assert VerificationMethod.KNOWLEDGE_BASED.value in result["methods_required"]
        assert "Additional verification methods required" in result["message"]


class TestStatisticsAndMonitoring:
    """Test verification statistics and monitoring."""
    
    @pytest.mark.asyncio
    async def test_verification_statistics(self, identity_verifier):
        """Test verification statistics collection."""
        # Perform some verification attempts
        await identity_verifier.initiate_verification("stats_user1", "user1@test.com")
        await identity_verifier.initiate_verification("stats_user2", "user2@test.com")
        
        # Complete one verification
        token = identity_verifier.active_tokens["stats_user1"]
        await identity_verifier.verify_email_token("stats_user1", token.token)
        
        # Fail one verification  
        await identity_verifier.verify_email_token("stats_user2", "000000")
        
        stats = await identity_verifier.get_verification_statistics()
        
        assert stats["total_attempts"] >= 3  # 2 initiations + 2 token attempts
        assert stats["successful_attempts"] >= 1
        assert stats["success_rate"] <= 1.0
        assert stats["active_tokens"] == 2
        assert "average_risk_score" in stats
        assert "methods_used" in stats
    
    @pytest.mark.asyncio
    async def test_token_cleanup(self, identity_verifier):
        """Test expired token cleanup."""
        # Create expired token
        user_id = "cleanup_user"
        await identity_verifier.initiate_verification(user_id, "cleanup@test.com")
        
        # Manually expire the token
        token = identity_verifier.active_tokens[user_id]
        token.expires_at = datetime.utcnow() - timedelta(minutes=1)
        
        # Run cleanup
        await identity_verifier.cleanup_expired_tokens()
        
        # Token should be removed
        assert user_id not in identity_verifier.active_tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])