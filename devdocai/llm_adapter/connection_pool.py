"""
M008: Connection Pooling and HTTP/2 Optimization for LLM Adapter.

Implements efficient connection management with:
- HTTP/2 connection pooling
- Keep-alive connections
- Connection health monitoring
- Automatic reconnection
- Provider-specific optimization
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Any, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import aiohttp
import ssl

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection states."""
    IDLE = "idle"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class ConnectionStats:
    """Statistics for a connection."""
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    requests_count: int = 0
    errors_count: int = 0
    total_response_time_ms: float = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    @property
    def average_response_time_ms(self) -> float:
        """Calculate average response time."""
        return (
            self.total_response_time_ms / self.requests_count
            if self.requests_count > 0 else 0
        )
    
    @property
    def uptime_seconds(self) -> float:
        """Calculate connection uptime."""
        return time.time() - self.created_at
    
    @property
    def idle_time_seconds(self) -> float:
        """Calculate idle time."""
        return time.time() - self.last_used


@dataclass
class PooledConnection:
    """Individual pooled connection."""
    session: aiohttp.ClientSession
    connector: aiohttp.TCPConnector
    state: ConnectionState
    provider: str
    base_url: str
    stats: ConnectionStats = field(default_factory=ConnectionStats)
    health_check_interval: float = 30.0  # seconds
    last_health_check: float = field(default_factory=time.time)
    
    async def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        if self.state != ConnectionState.ACTIVE:
            return False
        
        # Check if health check is needed
        if time.time() - self.last_health_check > self.health_check_interval:
            return await self._perform_health_check()
        
        return True
    
    async def _perform_health_check(self) -> bool:
        """Perform actual health check."""
        try:
            # Simple connectivity test
            async with self.session.head(
                self.base_url,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self.last_health_check = time.time()
                return response.status < 500
        except Exception as e:
            logger.warning(f"Health check failed for {self.provider}: {e}")
            return False
    
    async def close(self) -> None:
        """Close the connection."""
        self.state = ConnectionState.CLOSING
        try:
            await self.session.close()
            await self.connector.close()
            self.state = ConnectionState.CLOSED
        except Exception as e:
            logger.error(f"Error closing connection for {self.provider}: {e}")
            self.state = ConnectionState.ERROR


class ConnectionPool:
    """
    HTTP/2 connection pool for a single provider.
    
    Features:
    - Connection lifecycle management
    - Automatic scaling based on load
    - Health monitoring
    - Connection warming
    """
    
    def __init__(
        self,
        provider: str,
        base_url: str,
        min_connections: int = 2,
        max_connections: int = 10,
        connection_timeout: float = 30.0,
        keep_alive_timeout: float = 60.0,
        enable_http2: bool = True
    ):
        """
        Initialize connection pool.
        
        Args:
            provider: Provider name
            base_url: Base URL for provider
            min_connections: Minimum connections to maintain
            max_connections: Maximum connections allowed
            connection_timeout: Connection timeout in seconds
            keep_alive_timeout: Keep-alive timeout in seconds
            enable_http2: Enable HTTP/2 support
        """
        self.provider = provider
        self.base_url = base_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.keep_alive_timeout = keep_alive_timeout
        self.enable_http2 = enable_http2
        
        # Connection storage
        self.connections: List[PooledConnection] = []
        self.available_connections: asyncio.Queue = asyncio.Queue()
        self.active_connections: Set[PooledConnection] = set()
        
        # Statistics
        self.total_connections_created = 0
        self.total_connections_closed = 0
        self.total_requests = 0
        
        self._lock = asyncio.Lock()
        self._closing = False
        
        self.logger = logging.getLogger(f"{__name__}.ConnectionPool.{provider}")
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        # Create minimum connections
        for _ in range(self.min_connections):
            conn = await self._create_connection()
            if conn:
                self.connections.append(conn)
                await self.available_connections.put(conn)
        
        self.logger.info(
            f"Initialized pool with {len(self.connections)} connections "
            f"for {self.provider}"
        )
    
    def _create_connector(self) -> aiohttp.TCPConnector:
        """Create optimized connector."""
        # SSL context for HTTP/2
        ssl_context = ssl.create_default_context()
        if self.enable_http2:
            ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
        
        return aiohttp.TCPConnector(
            limit=self.max_connections,
            limit_per_host=self.max_connections,
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            enable_cleanup_closed=True,
            force_close=False,
            keepalive_timeout=self.keep_alive_timeout,
            ssl=ssl_context
        )
    
    async def _create_connection(self) -> Optional[PooledConnection]:
        """Create new connection."""
        try:
            connector = self._create_connector()
            
            # Create session with optimized settings
            timeout = aiohttp.ClientTimeout(
                total=self.connection_timeout,
                connect=10,
                sock_connect=10,
                sock_read=30
            )
            
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Connection': 'keep-alive',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'User-Agent': f'DevDocAI-LLMAdapter/3.0.0 ({self.provider})'
                },
                # Enable response compression
                auto_decompress=True,
                # Connection pooling settings
                connector_owner=True,
                # Trust environment SSL settings
                trust_env=True
            )
            
            connection = PooledConnection(
                session=session,
                connector=connector,
                state=ConnectionState.ACTIVE,
                provider=self.provider,
                base_url=self.base_url
            )
            
            self.total_connections_created += 1
            
            self.logger.debug(f"Created new connection for {self.provider}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to create connection for {self.provider}: {e}")
            return None
    
    async def acquire(self, timeout: Optional[float] = None) -> PooledConnection:
        """
        Acquire connection from pool.
        
        Args:
            timeout: Acquisition timeout
            
        Returns:
            Available connection
            
        Raises:
            TimeoutError: If acquisition times out
            RuntimeError: If pool is closing
        """
        if self._closing:
            raise RuntimeError("Connection pool is closing")
        
        timeout = timeout or self.connection_timeout
        
        try:
            # Try to get available connection
            connection = await asyncio.wait_for(
                self.available_connections.get(),
                timeout=timeout
            )
            
            # Check health
            if not await connection.is_healthy():
                # Connection unhealthy, create new one
                await connection.close()
                self.connections.remove(connection)
                
                connection = await self._create_connection()
                if not connection:
                    raise RuntimeError(f"Failed to create connection for {self.provider}")
                
                self.connections.append(connection)
            
            # Mark as active
            self.active_connections.add(connection)
            connection.stats.last_used = time.time()
            
            return connection
            
        except asyncio.TimeoutError:
            # Check if we can create new connection
            async with self._lock:
                if len(self.connections) < self.max_connections:
                    connection = await self._create_connection()
                    if connection:
                        self.connections.append(connection)
                        self.active_connections.add(connection)
                        return connection
            
            raise TimeoutError(f"Failed to acquire connection for {self.provider}")
    
    async def release(self, connection: PooledConnection) -> None:
        """
        Release connection back to pool.
        
        Args:
            connection: Connection to release
        """
        if connection in self.active_connections:
            self.active_connections.remove(connection)
        
        if connection.state == ConnectionState.ACTIVE:
            # Return to available pool
            await self.available_connections.put(connection)
        else:
            # Connection is bad, remove it
            if connection in self.connections:
                self.connections.remove(connection)
            await connection.close()
            
            # Create replacement if below minimum
            async with self._lock:
                if len(self.connections) < self.min_connections:
                    new_conn = await self._create_connection()
                    if new_conn:
                        self.connections.append(new_conn)
                        await self.available_connections.put(new_conn)
    
    async def execute_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Execute HTTP request using pooled connection.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
        """
        connection = await self.acquire()
        
        try:
            start_time = time.time()
            
            # Execute request
            async with connection.session.request(method, url, **kwargs) as response:
                # Update statistics
                connection.stats.requests_count += 1
                connection.stats.total_response_time_ms += (time.time() - start_time) * 1000
                
                # Track bytes if available
                if hasattr(response, 'content_length') and response.content_length:
                    connection.stats.bytes_received += response.content_length
                
                self.total_requests += 1
                
                return response
                
        except Exception as e:
            connection.stats.errors_count += 1
            connection.state = ConnectionState.ERROR
            raise
        finally:
            await self.release(connection)
    
    async def close_idle_connections(self, max_idle_seconds: float = 300) -> int:
        """
        Close connections that have been idle too long.
        
        Args:
            max_idle_seconds: Maximum idle time
            
        Returns:
            Number of connections closed
        """
        closed = 0
        
        async with self._lock:
            connections_to_close = []
            
            for conn in self.connections:
                if (
                    conn not in self.active_connections and
                    conn.stats.idle_time_seconds > max_idle_seconds and
                    len(self.connections) > self.min_connections
                ):
                    connections_to_close.append(conn)
            
            for conn in connections_to_close:
                await conn.close()
                self.connections.remove(conn)
                self.total_connections_closed += 1
                closed += 1
        
        if closed > 0:
            self.logger.info(f"Closed {closed} idle connections for {self.provider}")
        
        return closed
    
    async def warm_connections(self) -> None:
        """Warm up connections by performing health checks."""
        tasks = []
        for conn in self.connections:
            if conn not in self.active_connections:
                tasks.append(conn.is_healthy())
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            healthy = sum(1 for r in results if r is True)
            self.logger.debug(
                f"Warmed {healthy}/{len(tasks)} connections for {self.provider}"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        active_count = len(self.active_connections)
        available_count = self.available_connections.qsize()
        
        # Calculate aggregate stats
        total_response_time = sum(
            conn.stats.total_response_time_ms
            for conn in self.connections
        )
        total_request_count = sum(
            conn.stats.requests_count
            for conn in self.connections
        )
        
        return {
            "provider": self.provider,
            "total_connections": len(self.connections),
            "active_connections": active_count,
            "available_connections": available_count,
            "total_connections_created": self.total_connections_created,
            "total_connections_closed": self.total_connections_closed,
            "total_requests": self.total_requests,
            "average_response_time_ms": (
                total_response_time / total_request_count
                if total_request_count > 0 else 0
            ),
            "http2_enabled": self.enable_http2,
            "connection_health": [
                {
                    "state": conn.state.value,
                    "requests": conn.stats.requests_count,
                    "errors": conn.stats.errors_count,
                    "idle_seconds": conn.stats.idle_time_seconds
                }
                for conn in self.connections
            ]
        }
    
    async def shutdown(self) -> None:
        """Shutdown the connection pool."""
        self._closing = True
        
        # Close all connections
        for conn in self.connections:
            await conn.close()
            self.total_connections_closed += 1
        
        self.connections.clear()
        self.active_connections.clear()
        
        self.logger.info(f"Shutdown connection pool for {self.provider}")


class ConnectionManager:
    """
    Manager for multiple connection pools.
    
    Coordinates connection pools across providers with:
    - Centralized management
    - Load balancing
    - Resource optimization
    - Global statistics
    """
    
    def __init__(
        self,
        enable_http2: bool = True,
        global_max_connections: int = 100,
        connection_ttl_seconds: float = 3600
    ):
        """
        Initialize connection manager.
        
        Args:
            enable_http2: Enable HTTP/2 globally
            global_max_connections: Total max connections across all pools
            connection_ttl_seconds: Connection TTL
        """
        self.enable_http2 = enable_http2
        self.global_max_connections = global_max_connections
        self.connection_ttl = connection_ttl_seconds
        
        # Provider pools
        self.pools: Dict[str, ConnectionPool] = {}
        
        # Maintenance task
        self.maintenance_task: Optional[asyncio.Task] = None
        self.maintenance_interval = 60  # seconds
        
        self.logger = logging.getLogger(f"{__name__}.ConnectionManager")
    
    async def create_pool(
        self,
        provider: str,
        base_url: str,
        min_connections: int = 2,
        max_connections: int = 10
    ) -> ConnectionPool:
        """
        Create connection pool for provider.
        
        Args:
            provider: Provider name
            base_url: Base URL
            min_connections: Minimum connections
            max_connections: Maximum connections
            
        Returns:
            Created connection pool
        """
        # Calculate max connections based on global limit
        current_total = sum(
            pool.max_connections for pool in self.pools.values()
        )
        
        if current_total + max_connections > self.global_max_connections:
            max_connections = max(
                1,
                self.global_max_connections - current_total
            )
            self.logger.warning(
                f"Limiting {provider} to {max_connections} connections "
                f"due to global limit"
            )
        
        pool = ConnectionPool(
            provider=provider,
            base_url=base_url,
            min_connections=min_connections,
            max_connections=max_connections,
            enable_http2=self.enable_http2
        )
        
        await pool.initialize()
        self.pools[provider] = pool
        
        # Start maintenance if not running
        if not self.maintenance_task or self.maintenance_task.done():
            self.maintenance_task = asyncio.create_task(self._maintenance_loop())
        
        self.logger.info(
            f"Created connection pool for {provider} "
            f"(min={min_connections}, max={max_connections})"
        )
        
        return pool
    
    def get_pool(self, provider: str) -> Optional[ConnectionPool]:
        """Get connection pool for provider."""
        return self.pools.get(provider)
    
    async def _maintenance_loop(self) -> None:
        """Periodic maintenance of connection pools."""
        while self.pools:
            try:
                await asyncio.sleep(self.maintenance_interval)
                
                # Close idle connections
                for pool in self.pools.values():
                    await pool.close_idle_connections()
                
                # Warm active connections
                for pool in self.pools.values():
                    await pool.warm_connections()
                
                # Log statistics
                stats = self.get_global_stats()
                self.logger.debug(
                    f"Connection stats: {stats['total_active']} active, "
                    f"{stats['total_available']} available, "
                    f"{stats['total_connections']} total"
                )
                
            except Exception as e:
                self.logger.error(f"Maintenance error: {e}")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global connection statistics."""
        stats = {
            "total_pools": len(self.pools),
            "total_connections": 0,
            "total_active": 0,
            "total_available": 0,
            "total_requests": 0,
            "pools": {}
        }
        
        for provider, pool in self.pools.items():
            pool_stats = pool.get_stats()
            stats["pools"][provider] = pool_stats
            stats["total_connections"] += pool_stats["total_connections"]
            stats["total_active"] += pool_stats["active_connections"]
            stats["total_available"] += pool_stats["available_connections"]
            stats["total_requests"] += pool_stats["total_requests"]
        
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown all connection pools."""
        # Cancel maintenance
        if self.maintenance_task:
            self.maintenance_task.cancel()
        
        # Shutdown all pools
        for pool in self.pools.values():
            await pool.shutdown()
        
        self.pools.clear()
        self.logger.info("Connection manager shutdown complete")