"""
Template Sandbox for M006 Template Registry.

This module provides a sandboxed execution environment for templates,
preventing code execution, system access, and other security risks.
"""

import ast
import time
import threading
from typing import Dict, Any, Optional, List, Set, Callable
from contextlib import contextmanager
import resource
import signal
import logging
from functools import wraps

from .exceptions import (
    TemplateSandboxError,
    TemplateTimeoutError,
    TemplateMemoryError,
    TemplateRecursionError
)

logger = logging.getLogger(__name__)


class TemplateSandbox:
    """
    Sandboxed execution environment for template operations.
    
    Provides:
    - Restricted execution context
    - Resource limits (CPU, memory, time)
    - Safe expression evaluation
    - Blocked dangerous operations
    - Recursion depth limits
    """
    
    # Resource limits
    MAX_MEMORY_MB = 100  # Maximum memory usage in MB
    MAX_EXECUTION_TIME = 5.0  # Maximum execution time in seconds
    MAX_RECURSION_DEPTH = 50  # Maximum recursion depth
    MAX_EXPRESSION_LENGTH = 1000  # Maximum expression length
    
    # Safe built-in functions whitelist
    SAFE_BUILTINS = {
        # Type conversions
        'str', 'int', 'float', 'bool',
        # Collections
        'list', 'dict', 'tuple', 'set',
        # Math operations
        'abs', 'min', 'max', 'sum', 'round',
        # String operations
        'len', 'format',
        # Logic
        'all', 'any',
        # Safe utilities
        'enumerate', 'range', 'zip', 'sorted',
    }
    
    # Blocked attributes and methods
    BLOCKED_ATTRS = {
        '__class__', '__base__', '__subclasses__', '__import__',
        '__builtins__', '__globals__', '__code__', '__closure__',
        '__dict__', '__module__', '__name__', '__qualname__',
        '__annotations__', '__doc__', '__file__', '__loader__',
        '__package__', '__spec__', '__cached__', '__path__',
        'im_class', 'im_func', 'im_self', 'func_code', 'func_globals',
        'gi_code', 'gi_frame', 'gi_running', 'gi_yieldfrom',
        'cr_await', 'cr_code', 'cr_frame', 'cr_origin', 'cr_running',
    }
    
    # Blocked modules
    BLOCKED_MODULES = {
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'requests',
        'importlib', 'builtins', '__builtin__', 'compile', 'exec',
        'eval', 'open', 'input', 'file', 'fileinput', 'tempfile',
        'shutil', 'glob', 'pickle', 'marshal', 'shelve', 'dbm',
        'sqlite3', 'asyncio', 'threading', 'multiprocessing',
    }
    
    def __init__(self,
                 max_memory_mb: Optional[int] = None,
                 max_execution_time: Optional[float] = None,
                 max_recursion_depth: Optional[int] = None):
        """
        Initialize sandbox.
        
        Args:
            max_memory_mb: Maximum memory usage in MB
            max_execution_time: Maximum execution time in seconds
            max_recursion_depth: Maximum recursion depth
        """
        self.max_memory_mb = max_memory_mb or self.MAX_MEMORY_MB
        self.max_execution_time = max_execution_time or self.MAX_EXECUTION_TIME
        self.max_recursion_depth = max_recursion_depth or self.MAX_RECURSION_DEPTH
        
        # Execution state
        self._execution_start_time: Optional[float] = None
        self._timeout_timer: Optional[threading.Timer] = None
        self._recursion_depth = 0
        
    @contextmanager
    def sandboxed_context(self, timeout: Optional[float] = None):
        """
        Create a sandboxed execution context.
        
        Args:
            timeout: Optional timeout override
            
        Yields:
            Sandboxed context
        """
        # Set resource limits
        old_limits = self._set_resource_limits()
        
        # Set timeout
        timeout = timeout or self.max_execution_time
        self._execution_start_time = time.time()
        
        # Set up timeout handler
        def timeout_handler():
            raise TemplateTimeoutError(f"Execution exceeded {timeout}s timeout")
        
        self._timeout_timer = threading.Timer(timeout, timeout_handler)
        self._timeout_timer.start()
        
        try:
            yield self
        finally:
            # Cancel timeout timer
            if self._timeout_timer:
                self._timeout_timer.cancel()
                self._timeout_timer = None
            
            # Restore resource limits
            self._restore_resource_limits(old_limits)
            
            self._execution_start_time = None
    
    def _set_resource_limits(self) -> Dict[int, tuple]:
        """Set resource limits for sandboxed execution."""
        old_limits = {}
        
        try:
            # Set memory limit (virtual memory)
            if hasattr(resource, 'RLIMIT_AS'):
                old_limits[resource.RLIMIT_AS] = resource.getrlimit(resource.RLIMIT_AS)
                memory_limit = self.max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # Set CPU time limit
            if hasattr(resource, 'RLIMIT_CPU'):
                old_limits[resource.RLIMIT_CPU] = resource.getrlimit(resource.RLIMIT_CPU)
                cpu_limit = int(self.max_execution_time) + 1
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            
        except Exception as e:
            logger.warning(f"Could not set resource limits: {e}")
        
        return old_limits
    
    def _restore_resource_limits(self, old_limits: Dict[int, tuple]) -> None:
        """Restore original resource limits."""
        for limit_type, limit_value in old_limits.items():
            try:
                resource.setrlimit(limit_type, limit_value)
            except Exception as e:
                logger.warning(f"Could not restore resource limit {limit_type}: {e}")
    
    def safe_eval(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        Safely evaluate an expression in sandboxed context.
        
        Args:
            expression: Expression to evaluate
            context: Variable context
            
        Returns:
            Evaluation result
            
        Raises:
            TemplateSandboxError: If expression is unsafe
        """
        # Check expression length
        if len(expression) > self.MAX_EXPRESSION_LENGTH:
            raise TemplateSandboxError(
                f"Expression too long ({len(expression)} > {self.MAX_EXPRESSION_LENGTH})"
            )
        
        # Check for blocked patterns
        self._validate_expression(expression)
        
        # Parse expression to AST
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise TemplateSandboxError(f"Invalid expression syntax: {e}")
        
        # Validate AST nodes
        self._validate_ast(tree)
        
        # Create safe context
        safe_context = self._create_safe_context(context)
        
        # Evaluate with timeout
        with self.sandboxed_context():
            try:
                # Compile and evaluate
                code = compile(tree, '<sandboxed>', 'eval')
                result = eval(code, {"__builtins__": {}}, safe_context)
                
                return result
                
            except TemplateTimeoutError:
                raise
            except MemoryError:
                raise TemplateMemoryError("Memory limit exceeded during evaluation")
            except RecursionError:
                raise TemplateRecursionError("Maximum recursion depth exceeded")
            except Exception as e:
                raise TemplateSandboxError(f"Evaluation failed: {e}")
    
    def _validate_expression(self, expression: str) -> None:
        """Validate expression for dangerous patterns."""
        expr_lower = expression.lower()
        
        # Check for import statements
        if 'import' in expr_lower:
            raise TemplateSandboxError("Import statements not allowed")
        
        # Check for blocked attributes
        for attr in self.BLOCKED_ATTRS:
            if attr in expression:
                raise TemplateSandboxError(f"Blocked attribute '{attr}' detected")
        
        # Check for blocked modules
        for module in self.BLOCKED_MODULES:
            if module in expr_lower:
                raise TemplateSandboxError(f"Blocked module '{module}' detected")
        
        # Check for exec/eval
        if 'exec' in expr_lower or 'eval' in expr_lower:
            raise TemplateSandboxError("exec/eval not allowed")
        
        # Check for file operations
        if 'open(' in expression or 'file(' in expression:
            raise TemplateSandboxError("File operations not allowed")
    
    def _validate_ast(self, tree: ast.AST) -> None:
        """Validate AST nodes for safety."""
        
        class SafetyValidator(ast.NodeVisitor):
            """AST visitor to validate node safety."""
            
            def __init__(self, sandbox):
                self.sandbox = sandbox
                
            def visit_Import(self, node):
                raise TemplateSandboxError("Import statements not allowed")
            
            def visit_ImportFrom(self, node):
                raise TemplateSandboxError("Import statements not allowed")
            
            def visit_FunctionDef(self, node):
                raise TemplateSandboxError("Function definitions not allowed")
            
            def visit_ClassDef(self, node):
                raise TemplateSandboxError("Class definitions not allowed")
            
            def visit_Lambda(self, node):
                raise TemplateSandboxError("Lambda functions not allowed")
            
            def visit_Exec(self, node):
                raise TemplateSandboxError("Exec not allowed")
            
            def visit_Global(self, node):
                raise TemplateSandboxError("Global statements not allowed")
            
            def visit_Nonlocal(self, node):
                raise TemplateSandboxError("Nonlocal statements not allowed")
            
            def visit_Attribute(self, node):
                # Check for blocked attributes
                if isinstance(node.attr, str) and node.attr in self.sandbox.BLOCKED_ATTRS:
                    raise TemplateSandboxError(f"Blocked attribute '{node.attr}'")
                self.generic_visit(node)
            
            def visit_Name(self, node):
                # Check for blocked names
                if node.id in self.sandbox.BLOCKED_MODULES:
                    raise TemplateSandboxError(f"Blocked module '{node.id}'")
                self.generic_visit(node)
        
        validator = SafetyValidator(self)
        validator.visit(tree)
    
    def _create_safe_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe execution context."""
        safe_context = {}
        
        # Add safe built-ins
        safe_builtins = {
            name: getattr(__builtins__, name) 
            for name in self.SAFE_BUILTINS 
            if hasattr(__builtins__, name)
        }
        
        # Add user context (shallow copy to prevent modification)
        for key, value in context.items():
            # Validate key name
            if key.startswith('__') or key in self.BLOCKED_ATTRS:
                logger.warning(f"Skipping unsafe context key: {key}")
                continue
            
            # Add to safe context
            safe_context[key] = value
        
        # Add safe built-ins to context
        safe_context.update(safe_builtins)
        
        return safe_context
    
    def safe_string_format(self, template: str, **kwargs) -> str:
        """
        Safely format a string template.
        
        Args:
            template: String template with {} placeholders
            **kwargs: Values to format into template
            
        Returns:
            Formatted string
            
        Raises:
            TemplateSandboxError: If formatting fails
        """
        try:
            # Use safe string formatting (no format_map or f-strings)
            return template.format(**kwargs)
        except (KeyError, ValueError, IndexError) as e:
            raise TemplateSandboxError(f"String formatting failed: {e}")
    
    def with_recursion_limit(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with recursion depth limit.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            TemplateRecursionError: If recursion limit exceeded
        """
        self._recursion_depth += 1
        
        try:
            if self._recursion_depth > self.max_recursion_depth:
                raise TemplateRecursionError(
                    f"Maximum recursion depth ({self.max_recursion_depth}) exceeded"
                )
            
            return func(*args, **kwargs)
            
        finally:
            self._recursion_depth -= 1
    
    def check_timeout(self) -> None:
        """
        Check if execution has timed out.
        
        Raises:
            TemplateTimeoutError: If timeout exceeded
        """
        if self._execution_start_time:
            elapsed = time.time() - self._execution_start_time
            if elapsed > self.max_execution_time:
                raise TemplateTimeoutError(
                    f"Execution time ({elapsed:.2f}s) exceeded limit ({self.max_execution_time}s)"
                )


class SafeTemplateContext:
    """
    Safe context wrapper for template variables.
    
    Prevents access to dangerous attributes and methods.
    """
    
    def __init__(self, data: Dict[str, Any], sandbox: TemplateSandbox):
        """
        Initialize safe context.
        
        Args:
            data: Context data
            sandbox: Sandbox instance
        """
        self._data = data
        self._sandbox = sandbox
    
    def __getitem__(self, key: str) -> Any:
        """Get item from context."""
        # Validate key
        if key in self._sandbox.BLOCKED_ATTRS:
            raise TemplateSandboxError(f"Access to '{key}' is blocked")
        
        # Check for special attributes
        if key.startswith('__'):
            raise TemplateSandboxError(f"Access to '{key}' is blocked")
        
        return self._data.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Set item in context."""
        # Validate key
        if key in self._sandbox.BLOCKED_ATTRS:
            raise TemplateSandboxError(f"Setting '{key}' is blocked")
        
        if key.startswith('__'):
            raise TemplateSandboxError(f"Setting '{key}' is blocked")
        
        self._data[key] = value
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in context."""
        return key in self._data
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get item with default."""
        try:
            return self[key]
        except (KeyError, TemplateSandboxError):
            return default
    
    def keys(self) -> List[str]:
        """Get context keys."""
        return [k for k in self._data.keys() 
                if not k.startswith('__') and k not in self._sandbox.BLOCKED_ATTRS]
    
    def values(self) -> List[Any]:
        """Get context values."""
        return [self._data[k] for k in self.keys()]
    
    def items(self) -> List[tuple]:
        """Get context items."""
        return [(k, self._data[k]) for k in self.keys()]