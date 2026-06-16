"""
Resilience patterns: retry logic, circuit breaker, and error recovery
"""
import logging
import asyncio
import time
from typing import Optional, Any, Callable, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import random

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failures exceed threshold
    HALF_OPEN = "half_open"    # Testing if service recovered


@dataclass
class CircuitBreakerState:
    """Track circuit breaker state for an endpoint"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    
    def is_timeout_exceeded(self, timeout_seconds: int) -> bool:
        """Check if timeout has elapsed since last failure"""
        if self.last_failure_time is None:
            return False
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= timeout_seconds


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_retries: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    jitter: bool = True


class RetryPolicy:
    """Implements exponential backoff retry strategy with jitter"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def get_delay_ms(self, attempt: int) -> float:
        """
        Calculate delay for given attempt with exponential backoff
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in milliseconds
        """
        # Exponential backoff: initial_delay * (base ^ attempt)
        delay = self.config.initial_delay_ms * (self.config.exponential_base ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay_ms)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            # Add random jitter: ±25% of delay
            jitter_range = delay * 0.25
            delay = delay + random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    async def execute_async(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute async function with retry logic
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result on success
            
        Raises:
            Exception from func if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.config.max_retries + 1} - {func.__name__}")
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"✓ {func.__name__} succeeded on attempt {attempt + 1}")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    delay_ms = self.get_delay_ms(attempt)
                    delay_s = delay_ms / 1000
                    logger.warning(
                        f"✗ {func.__name__} attempt {attempt + 1} failed: {str(e)[:100]}. "
                        f"Retrying in {delay_ms:.0f}ms..."
                    )
                    await asyncio.sleep(delay_s)
                else:
                    logger.error(
                        f"✗ {func.__name__} failed after {self.config.max_retries + 1} attempts: {str(e)}"
                    )
        
        raise last_exception


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceed threshold, requests fail fast
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 30,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Consecutive failures to open circuit
            recovery_timeout_seconds: Wait before attempting recovery
            success_threshold: Consecutive successes to close circuit from half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.success_threshold = success_threshold
        
        # Track state per endpoint
        self.states: Dict[str, CircuitBreakerState] = {}
    
    def _get_state(self, endpoint: str) -> CircuitBreakerState:
        """Get or create state for endpoint"""
        if endpoint not in self.states:
            self.states[endpoint] = CircuitBreakerState()
        return self.states[endpoint]
    
    def record_success(self, endpoint: str):
        """Record successful call"""
        state = self._get_state(endpoint)
        
        if state.state == CircuitState.HALF_OPEN:
            state.success_count += 1
            
            if state.success_count >= self.success_threshold:
                logger.info(f"✓ Circuit CLOSED for {endpoint} (recovered after {state.failure_count} failures)")
                state.state = CircuitState.CLOSED
                state.failure_count = 0
                state.success_count = 0
        else:
            # CLOSED state: reset failure count on success
            state.failure_count = 0
            state.success_count = 0
    
    def record_failure(self, endpoint: str):
        """Record failed call"""
        state = self._get_state(endpoint)
        state.failure_count += 1
        state.last_failure_time = datetime.utcnow()
        
        if state.state == CircuitState.CLOSED:
            if state.failure_count >= self.failure_threshold:
                logger.error(
                    f"✗ Circuit OPENED for {endpoint} "
                    f"({state.failure_count} consecutive failures)"
                )
                state.state = CircuitState.OPEN
        
        elif state.state == CircuitState.HALF_OPEN:
            # Any failure while half-open goes back to open
            logger.warning(f"✗ Circuit reopened for {endpoint} (failed during recovery)")
            state.state = CircuitState.OPEN
            state.success_count = 0
    
    def can_execute(self, endpoint: str) -> bool:
        """Check if request can be executed"""
        state = self._get_state(endpoint)
        
        if state.state == CircuitState.CLOSED:
            return True
        
        if state.state == CircuitState.OPEN:
            # Check if timeout elapsed to transition to half-open
            if state.is_timeout_exceeded(self.recovery_timeout_seconds):
                logger.info(
                    f"→ Circuit HALF-OPEN for {endpoint} "
                    f"(testing recovery after {self.recovery_timeout_seconds}s)"
                )
                state.state = CircuitState.HALF_OPEN
                state.failure_count = 0
                state.success_count = 0
                return True
            return False
        
        if state.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return True
        
        return False
    
    def get_status(self, endpoint: str) -> Dict[str, Any]:
        """Get circuit status for endpoint"""
        state = self._get_state(endpoint)
        return {
            "endpoint": endpoint,
            "state": state.state.value,
            "failure_count": state.failure_count,
            "success_count": state.success_count,
            "last_failure": state.last_failure_time.isoformat() if state.last_failure_time else None,
            "last_state_change": state.last_state_change.isoformat()
        }
    
    async def execute_async(
        self,
        endpoint: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            endpoint: Endpoint identifier (used for tracking state)
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result on success
            
        Raises:
            RuntimeError if circuit is open
            Exception from func if execution fails
        """
        if not self.can_execute(endpoint):
            raise RuntimeError(
                f"Circuit breaker is OPEN for {endpoint}. "
                f"Service unavailable. Retry after {self.recovery_timeout_seconds}s"
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success(endpoint)
            return result
        
        except Exception as e:
            self.record_failure(endpoint)
            raise


class ErrorRecovery:
    """Error recovery strategies for graceful degradation"""
    
    @staticmethod
    def should_use_fallback(error: Exception) -> bool:
        """Determine if error is recoverable with fallback"""
        # Timeout and connection errors are recoverable
        recoverable_errors = (
            asyncio.TimeoutError,
            ConnectionError,
            TimeoutError,
            OSError,
        )
        return isinstance(error, recoverable_errors)
    
    @staticmethod
    def get_fallback_value(
        service_name: str,
        cache_value: Optional[Any] = None,
        default_value: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Get fallback value for failed service call
        
        Priority:
        1. Last-known-good cached value
        2. Provided default value
        3. None
        """
        if cache_value is not None:
            logger.info(f"✓ Using cached fallback for {service_name}")
            return cache_value
        
        if default_value is not None:
            logger.info(f"✓ Using default fallback for {service_name}")
            return default_value
        
        logger.warning(f"✗ No fallback available for {service_name}")
        return None


@dataclass
class ServiceHealthStatus:
    """Health status of a service"""
    name: str
    is_healthy: bool
    last_check: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class HealthMonitor:
    """Monitor health of all services"""
    
    def __init__(self):
        self.services: Dict[str, ServiceHealthStatus] = {}
    
    def update_status(
        self,
        service_name: str,
        is_healthy: bool,
        details: Optional[Dict] = None,
        error_message: Optional[str] = None
    ):
        """Update service health status"""
        self.services[service_name] = ServiceHealthStatus(
            name=service_name,
            is_healthy=is_healthy,
            last_check=datetime.utcnow(),
            details=details or {},
            error_message=error_message
        )
        
        status_icon = "✓" if is_healthy else "✗"
        logger.info(f"{status_icon} {service_name}: {'healthy' if is_healthy else 'unhealthy'}")
    
    def get_status(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get health status"""
        if service_name:
            service = self.services.get(service_name)
            if service:
                return self._service_to_dict(service)
            return None
        
        return {
            name: self._service_to_dict(status)
            for name, status in self.services.items()
        }
    
    @staticmethod
    def _service_to_dict(service: ServiceHealthStatus) -> Dict[str, Any]:
        """Convert service status to dict"""
        return {
            "name": service.name,
            "is_healthy": service.is_healthy,
            "last_check": service.last_check.isoformat(),
            "details": service.details,
            "error_message": service.error_message
        }
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        if not self.services:
            return {"status": "unknown", "services": 0}
        
        total = len(self.services)
        healthy = sum(1 for s in self.services.values() if s.is_healthy)
        
        return {
            "status": "healthy" if healthy == total else "degraded" if healthy > 0 else "unhealthy",
            "healthy_services": healthy,
            "total_services": total,
            "health_percentage": (healthy / total) * 100 if total > 0 else 0
        }


# Global instances
retry_policy = RetryPolicy()
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout_seconds=30,
    success_threshold=2
)
health_monitor = HealthMonitor()
