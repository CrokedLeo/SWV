"""
Unit tests for security.py module
Tests: FileSecurityValidator, InputSanitizer, RequestValidator, EncryptionUtility
"""
import pytest
import re
from backend.security import (
    FileSecurityValidator, InputSanitizer, RequestValidator, 
    EncryptionUtility, APIKeyManager, SecurityHeaders, log_security_event
)


# ============= FILE SECURITY VALIDATOR TESTS =============

class TestFileSecurityValidator:
    """Test FileSecurityValidator class"""
    
    @pytest.mark.unit
    def test_validate_valid_jpeg_file(self):
        """Test validation of valid JPEG file"""
        clean_jpeg_bytes = b'\xFF\xD8\xFF' + b'JPEG_DATA' * 100
        is_valid, error = FileSecurityValidator.validate_file(
            clean_jpeg_bytes, "image.jpg"
        )
        assert is_valid
        assert error == ""
    
    @pytest.mark.unit
    def test_validate_valid_png_file(self):
        """Test validation of valid PNG file"""
        png_header = b'\x89PNG\r\n\x1a\n' + b'PNG_DATA' * 100
        is_valid, error = FileSecurityValidator.validate_file(
            png_header, "image.png"
        )
        assert is_valid
        assert error == ""
    
    @pytest.mark.unit
    def test_validate_valid_gif_file(self):
        """Test validation of valid GIF file"""
        gif_header = b'GIF87a' + b'GIF_DATA' * 100
        is_valid, error = FileSecurityValidator.validate_file(
            gif_header, "image.gif"
        )
        assert is_valid
        assert error == ""
    
    @pytest.mark.unit
    def test_file_exceeds_max_size(self):
        """Test file size validation"""
        jpeg_header = b'\xFF\xD8\xFF'
        oversized = jpeg_header + b'A' * (11 * 1024 * 1024)  # 11MB
        
        is_valid, error = FileSecurityValidator.validate_file(
            oversized, "image.jpg"
        )
        assert not is_valid
        assert "exceeds maximum size" in error
    
    @pytest.mark.unit
    def test_invalid_file_extension(self):
        """Test invalid file extension rejection"""
        jpeg_header = b'\xFF\xD8\xFF' + b'DATA' * 100
        is_valid, error = FileSecurityValidator.validate_file(
            jpeg_header, "image.exe"
        )
        assert not is_valid
        assert "File type not allowed" in error
    
    @pytest.mark.unit
    def test_missing_filename(self):
        """Test missing filename rejection"""
        jpeg_header = b'\xFF\xD8\xFF' + b'DATA' * 100
        is_valid, error = FileSecurityValidator.validate_file(
            jpeg_header, ""
        )
        assert not is_valid
        assert "No filename provided" in error
    
    @pytest.mark.unit
    def test_file_signature_takes_precedence_over_extension(self):
        """Test file signature is validated over extension"""
        # JPEG content with non-matching PNG extension — should validate by content
        jpeg_data = b'\xFF\xD8\xFF' + b'DATA' * 100
        is_valid, error = FileSecurityValidator.validate_file(
            jpeg_data, "image.png"
        )
        assert is_valid
    
    @pytest.mark.unit
    def test_file_with_embedded_script(self):
        """Test detection of embedded malicious script"""
        jpeg_header = b'\xFF\xD8\xFF'
        malicious = jpeg_header + b'<script>alert("xss")</script>' * 10
        
        is_valid, error = FileSecurityValidator.validate_file(
            malicious, "image.jpg"
        )
        assert not is_valid
        assert "suspicious patterns" in error
    
    @pytest.mark.unit
    def test_file_with_php_code(self):
        """Test detection of PHP code in file"""
        jpeg_header = b'\xFF\xD8\xFF'
        malicious = jpeg_header + b'<?php system("ls"); ?>' * 10
        
        is_valid, error = FileSecurityValidator.validate_file(
            malicious, "image.jpg"
        )
        assert not is_valid
        assert "suspicious patterns" in error
    
    @pytest.mark.unit
    def test_generate_safe_filename(self):
        """Test safe filename generation"""
        safe_name = FileSecurityValidator.generate_safe_filename("../../../etc/passwd")
        assert ".." not in safe_name
        assert "passwd" not in safe_name
        assert safe_name.startswith("upload_")
    
    @pytest.mark.unit
    def test_generate_safe_filename_preserves_extension(self):
        """Test safe filename preserves extension"""
        safe_name = FileSecurityValidator.generate_safe_filename("document.pdf")
        assert safe_name.endswith(".pdf")
    
    @pytest.mark.unit
    def test_file_too_small_no_signature(self):
        """Test file too small to have valid signature"""
        small_file = b'XX'  # Too small
        is_valid, error = FileSecurityValidator.validate_file(
            small_file, "image.jpg"
        )
        assert not is_valid
        assert "signature does not match" in error
    
    @pytest.mark.unit
    def test_custom_max_file_size(self):
        """Test validation with custom max file size"""
        jpeg_header = b'\xFF\xD8\xFF' + b'DATA' * 100
        is_valid, error = FileSecurityValidator.validate_file(
            jpeg_header, "image.jpg", max_size=500
        )
        # Small file should pass with custom limit
        assert is_valid


# ============= INPUT SANITIZER TESTS =============

class TestInputSanitizer:
    """Test InputSanitizer class"""
    
    @pytest.mark.unit
    def test_sanitize_string_normal(self):
        """Test sanitizing normal string"""
        result = InputSanitizer.sanitize_string("normal string")
        assert result == "normal string"
    
    @pytest.mark.unit
    def test_sanitize_string_removes_null_bytes(self):
        """Test null byte removal"""
        result = InputSanitizer.sanitize_string("hello\x00world")
        assert "\x00" not in result
        assert "helloworld" in result
    
    @pytest.mark.unit
    def test_sanitize_string_removes_control_characters(self):
        """Test control character removal"""
        result = InputSanitizer.sanitize_string("hello\x01\x02world")
        assert "\x01" not in result
        assert "\x02" not in result
    
    @pytest.mark.unit
    def test_sanitize_string_truncates_long_input(self):
        """Test truncation of long strings"""
        long_string = "a" * 1000
        result = InputSanitizer.sanitize_string(long_string, max_length=50)
        assert len(result) == 50
    
    @pytest.mark.unit
    def test_sanitize_string_custom_max_length(self):
        """Test custom max length"""
        result = InputSanitizer.sanitize_string("1234567890", max_length=5)
        assert result == "12345"
    
    @pytest.mark.unit
    def test_sanitize_string_empty(self):
        """Test sanitizing empty string"""
        result = InputSanitizer.sanitize_string("")
        assert result == ""
    
    @pytest.mark.unit
    def test_sanitize_string_none(self):
        """Test sanitizing None"""
        result = InputSanitizer.sanitize_string(None)
        assert result == ""
    
    @pytest.mark.unit
    def test_sanitize_number_within_range(self):
        """Test number sanitization within range"""
        result = InputSanitizer.sanitize_number(50, min_val=0, max_val=100)
        assert result == 50
    
    @pytest.mark.unit
    def test_sanitize_number_below_min(self):
        """Test number clamping to minimum"""
        result = InputSanitizer.sanitize_number(-10, min_val=0, max_val=100)
        assert result == 0
    
    @pytest.mark.unit
    def test_sanitize_number_above_max(self):
        """Test number clamping to maximum"""
        result = InputSanitizer.sanitize_number(150, min_val=0, max_val=100)
        assert result == 100
    
    @pytest.mark.unit
    def test_validate_email_valid_addresses(self, valid_email_samples):
        """Test valid email validation"""
        for email in valid_email_samples:
            assert InputSanitizer.validate_email(email)
    
    @pytest.mark.unit
    def test_validate_email_invalid_addresses(self, invalid_email_samples):
        """Test invalid email rejection"""
        for email in invalid_email_samples:
            assert not InputSanitizer.validate_email(email)
    
    @pytest.mark.unit
    def test_validate_url_valid_addresses(self, valid_url_samples):
        """Test valid URL validation"""
        for url in valid_url_samples:
            assert InputSanitizer.validate_url(url)
    
    @pytest.mark.unit
    def test_validate_url_invalid_addresses(self, invalid_url_samples):
        """Test invalid URL rejection"""
        for url in invalid_url_samples:
            assert not InputSanitizer.validate_url(url)


# ============= REQUEST VALIDATOR TESTS =============

class TestRequestValidator:
    """Test RequestValidator class"""
    
    @pytest.mark.unit
    def test_validate_coordinates_valid(self, sample_coordinates):
        """Test valid coordinate validation"""
        coords = sample_coordinates["valid"]
        is_valid, error = RequestValidator.validate_coordinates(coords["lat"], coords["lon"])
        assert is_valid
        assert error == ""
    
    @pytest.mark.unit
    def test_validate_coordinates_invalid_latitude_high(self, sample_coordinates):
        """Test invalid latitude (too high)"""
        coords = sample_coordinates["invalid_lat_high"]
        is_valid, error = RequestValidator.validate_coordinates(coords["lat"], coords["lon"])
        assert not is_valid
        assert "Latitude must be between -90 and 90" in error
    
    @pytest.mark.unit
    def test_validate_coordinates_invalid_latitude_low(self, sample_coordinates):
        """Test invalid latitude (too low)"""
        coords = sample_coordinates["invalid_lat_low"]
        is_valid, error = RequestValidator.validate_coordinates(coords["lat"], coords["lon"])
        assert not is_valid
    
    @pytest.mark.unit
    def test_validate_coordinates_invalid_longitude_high(self, sample_coordinates):
        """Test invalid longitude (too high)"""
        coords = sample_coordinates["invalid_lon_high"]
        is_valid, error = RequestValidator.validate_coordinates(coords["lat"], coords["lon"])
        assert not is_valid
        assert "Longitude must be between -180 and 180" in error
    
    @pytest.mark.unit
    def test_validate_coordinates_boundary_values(self, sample_coordinates):
        """Test boundary coordinate values"""
        # North pole
        coords = sample_coordinates["north_pole"]
        is_valid, error = RequestValidator.validate_coordinates(coords["lat"], coords["lon"])
        assert is_valid
        
        # South pole
        coords = sample_coordinates["south_pole"]
        is_valid, error = RequestValidator.validate_coordinates(coords["lat"], coords["lon"])
        assert is_valid
        
        # Equator
        coords = sample_coordinates["equator"]
        is_valid, error = RequestValidator.validate_coordinates(coords["lat"], coords["lon"])
        assert is_valid
    
    @pytest.mark.unit
    def test_validate_confidence_valid(self):
        """Test valid confidence values"""
        assert RequestValidator.validate_confidence(0.5)[0]
        assert RequestValidator.validate_confidence(0.1)[0]
        assert RequestValidator.validate_confidence(0.95)[0]
    
    @pytest.mark.unit
    def test_validate_confidence_invalid_zero(self):
        """Test confidence at zero boundary"""
        is_valid, error = RequestValidator.validate_confidence(0.0)
        assert not is_valid
    
    @pytest.mark.unit
    def test_validate_confidence_invalid_one(self):
        """Test confidence at one boundary"""
        is_valid, error = RequestValidator.validate_confidence(1.0)
        assert not is_valid
    
    @pytest.mark.unit
    def test_validate_confidence_invalid_negative(self):
        """Test negative confidence"""
        is_valid, error = RequestValidator.validate_confidence(-0.5)
        assert not is_valid
    
    @pytest.mark.unit
    def test_is_reasonable_processing_time_valid(self):
        """Test valid processing times"""
        assert RequestValidator.is_reasonable_processing_time(100)
        assert RequestValidator.is_reasonable_processing_time(5000)
        assert RequestValidator.is_reasonable_processing_time(59999)
    
    @pytest.mark.unit
    def test_is_reasonable_processing_time_invalid(self):
        """Test invalid processing times"""
        assert not RequestValidator.is_reasonable_processing_time(0)
        assert not RequestValidator.is_reasonable_processing_time(60001)
        assert not RequestValidator.is_reasonable_processing_time(-100)
    
    @pytest.mark.unit
    def test_is_reasonable_aqi_valid(self):
        """Test valid AQI values"""
        assert RequestValidator.is_reasonable_aqi(0)
        assert RequestValidator.is_reasonable_aqi(100)
        assert RequestValidator.is_reasonable_aqi(500)
    
    @pytest.mark.unit
    def test_is_reasonable_aqi_invalid(self):
        """Test invalid AQI values"""
        assert not RequestValidator.is_reasonable_aqi(-1)
        assert not RequestValidator.is_reasonable_aqi(501)
    
    @pytest.mark.unit
    def test_is_reasonable_smoke_percentage_valid(self):
        """Test valid smoke percentages"""
        assert RequestValidator.is_reasonable_smoke_percentage(0)
        assert RequestValidator.is_reasonable_smoke_percentage(50)
        assert RequestValidator.is_reasonable_smoke_percentage(100)
    
    @pytest.mark.unit
    def test_is_reasonable_smoke_percentage_invalid(self):
        """Test invalid smoke percentages"""
        assert not RequestValidator.is_reasonable_smoke_percentage(-0.1)
        assert not RequestValidator.is_reasonable_smoke_percentage(100.1)


# ============= ENCRYPTION UTILITY TESTS =============

class TestEncryptionUtility:
    """Test EncryptionUtility class"""
    
    @pytest.mark.unit
    def test_hash_string_creates_hash(self):
        """Test string hashing"""
        hashed = EncryptionUtility.hash_string("password")
        assert hashed is not None
        assert "$" in hashed  # Format is hash$salt
        assert len(hashed) > 32
    
    @pytest.mark.unit
    def test_hash_string_with_salt(self):
        """Test hashing with provided salt"""
        salt = "test_salt"
        hashed = EncryptionUtility.hash_string("password", salt=salt)
        assert salt in hashed
    
    @pytest.mark.unit
    def test_verify_hash_correct(self):
        """Test hash verification with correct password"""
        original = "password123"
        hashed = EncryptionUtility.hash_string(original)
        assert EncryptionUtility.verify_hash(original, hashed)
    
    @pytest.mark.unit
    def test_verify_hash_incorrect(self):
        """Test hash verification with incorrect password"""
        original = "password123"
        hashed = EncryptionUtility.hash_string(original)
        assert not EncryptionUtility.verify_hash("wrong_password", hashed)
    
    @pytest.mark.unit
    def test_generate_secure_token_length(self):
        """Test secure token generation length"""
        token = EncryptionUtility.generate_secure_token(length=32)
        assert len(token) > 0
        assert isinstance(token, str)
    
    @pytest.mark.unit
    def test_generate_secure_token_uniqueness(self):
        """Test secure token uniqueness"""
        token1 = EncryptionUtility.generate_secure_token()
        token2 = EncryptionUtility.generate_secure_token()
        assert token1 != token2
    
    @pytest.mark.unit
    def test_generate_secure_token_custom_length(self):
        """Test custom token length"""
        token = EncryptionUtility.generate_secure_token(length=16)
        assert len(token) > 0


# ============= API KEY MANAGER TESTS =============

class TestAPIKeyManager:
    """Test APIKeyManager class"""
    
    @pytest.mark.unit
    def test_generate_api_key(self):
        """Test API key generation"""
        key = APIKeyManager.generate_api_key()
        assert key is not None
        assert len(key) > 0
        assert isinstance(key, str)
    
    @pytest.mark.unit
    def test_generate_api_key_uniqueness(self):
        """Test API key uniqueness"""
        key1 = APIKeyManager.generate_api_key()
        key2 = APIKeyManager.generate_api_key()
        assert key1 != key2
    
    @pytest.mark.unit
    def test_hash_api_key(self):
        """Test API key hashing"""
        key = APIKeyManager.generate_api_key()
        hashed = APIKeyManager.hash_api_key(key)
        assert hashed is not None
        assert len(hashed) == 64  # SHA-256 hex digest
    
    @pytest.mark.unit
    def test_verify_api_key_correct(self):
        """Test API key verification with correct key"""
        key = APIKeyManager.generate_api_key()
        hashed = APIKeyManager.hash_api_key(key)
        assert APIKeyManager.verify_api_key(key, hashed)
    
    @pytest.mark.unit
    def test_verify_api_key_incorrect(self):
        """Test API key verification with incorrect key"""
        key1 = APIKeyManager.generate_api_key()
        key2 = APIKeyManager.generate_api_key()
        hashed = APIKeyManager.hash_api_key(key1)
        assert not APIKeyManager.verify_api_key(key2, hashed)


# ============= SECURITY HEADERS TESTS =============

class TestSecurityHeaders:
    """Test SecurityHeaders class"""
    
    @pytest.mark.unit
    def test_get_security_headers(self):
        """Test security headers generation"""
        headers = SecurityHeaders.get_security_headers()
        assert isinstance(headers, dict)
        assert len(headers) > 0
    
    @pytest.mark.unit
    def test_security_headers_content(self):
        """Test security headers contain expected values"""
        headers = SecurityHeaders.get_security_headers()
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
        assert "Referrer-Policy" in headers
    
    @pytest.mark.unit
    def test_security_headers_values(self):
        """Test security headers have correct values"""
        headers = SecurityHeaders.get_security_headers()
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert "1; mode=block" in headers["X-XSS-Protection"]


# ============= INTEGRATION TESTS =============

class TestSecurityIntegration:
    """Integration tests for security module"""
    
    @pytest.mark.integration
    def test_file_upload_security_workflow(self):
        """Test complete file upload security workflow"""
        # Create valid image
        jpeg_header = b'\xFF\xD8\xFF' + b'JPEG_DATA' * 100
        
        # Validate
        is_valid, error = FileSecurityValidator.validate_file(jpeg_header, "photo.jpg")
        assert is_valid
        
        # Generate safe filename
        safe_name = FileSecurityValidator.generate_safe_filename("../../../photo.jpg")
        assert safe_name != "photo.jpg"
        assert safe_name.endswith(".jpg")
    
    @pytest.mark.integration
    def test_input_sanitization_xss_prevention(self, xss_injection_samples):
        """Test XSS prevention through input sanitization"""
        for payload in xss_injection_samples:
            sanitized = InputSanitizer.sanitize_string(payload)
            # Sanitized string should not contain script tags or javascript
            assert "<script" not in sanitized.lower() or "script" not in payload.lower()
    
    @pytest.mark.integration
    def test_encryption_decryption_cycle(self):
        """Test encryption and decryption cycle"""
        original_value = "secret_api_key_12345"
        
        # Hash it
        hashed = EncryptionUtility.hash_string(original_value)
        
        # Verify it
        assert EncryptionUtility.verify_hash(original_value, hashed)
        
        # Wrong value should not verify
        assert not EncryptionUtility.verify_hash("wrong_value", hashed)
