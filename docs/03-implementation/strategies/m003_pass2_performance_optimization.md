# M003 MIAIR Engine - Pass 2 Performance Optimization Strategy

## Executive Summary

**Current Status**: M003 Pass 1 is complete with 90.91% test coverage and working Shannon entropy optimization.

**Performance Target**: 248,000 documents/minute (4,133 docs/sec)

**Current Performance**: 3,638 docs/minute (60.6 docs/sec) with mock LLM

**Required Speedup**: 68.2x

## Performance Analysis Results

### Current Performance Characteristics

| Component | Performance | Status |
|-----------|------------|--------|
| Shannon Entropy Calculation | 8,079 docs/sec | ✅ EXCEEDS TARGET |
| Quality Measurement | 8,206 docs/sec | ✅ EXCEEDS TARGET |
| Cache Effectiveness | 38.9x speedup | ✅ GOOD |
| Optimization Pipeline | 60.6 docs/sec | ❌ BOTTLENECK |
| Parallel Speedup | 3.1x (of 4x possible) | ⚠️ SUBOPTIMAL |

### Bottleneck Identification

1. **Primary Bottleneck**: LLM API calls (50ms latency per call)
   - Each document requires 1-7 LLM calls (iterations)
   - Sequential processing limits throughput
   - Current parallel efficiency: 77.5%

2. **Secondary Issues**:
   - Batch size too small (100 docs)
   - Worker count too low (4 workers)
   - No async processing for I/O operations
   - Tokenization using regex (could be 10x faster)

## Optimization Strategy

### Phase 1: Quick Wins (2-3x speedup)

#### 1.1 Increase Parallelization
```python
# Current
self.max_workers = config.get("performance.max_workers", 4)
self.batch_size = config.get("performance.batch_size", 100)

# Optimized
self.max_workers = config.get("performance.max_workers", 16)
self.batch_size = config.get("performance.batch_size", 1000)
```

#### 1.2 Compile Regex Patterns
```python
# Current (compiled once per call)
words = re.findall(r"\b\w+\b", text.lower())

# Optimized (compile once, reuse)
class MetricsCalculator:
    WORD_PATTERN = re.compile(r"\b\w+\b")

    def tokenize(self, text: str) -> List[str]:
        return self.WORD_PATTERN.findall(text.lower())
```

#### 1.3 Optimize Cache Key Generation
```python
# Current
cache_key = f"entropy:{hashlib.sha256(validated.encode()).hexdigest()[:16]}"

# Optimized (use faster hash)
cache_key = f"e:{hashlib.blake2b(validated.encode(), digest_size=8).hexdigest()}"
```

### Phase 2: Async Processing (10-20x speedup)

#### 2.1 Async LLM Calls
```python
async def refine_content_async(self, document: str, metrics: Optional[DocumentMetrics] = None) -> str:
    """Async version of content refinement."""
    # Prepare prompt
    prompt = self.strategy.build_refinement_prompt(document, metrics)

    # Async LLM call
    response = await self.llm_adapter.query_async(
        prompt,
        max_tokens=2000,
        temperature=0.7
    )

    return response.content

async def batch_optimize_async_parallel(self, documents: List[str]) -> List[OptimizationResult]:
    """Process documents with maximum parallelization."""
    # Create tasks for all documents
    tasks = []
    for doc in documents:
        task = self.optimize_async(doc, max_iterations=1)
        tasks.append(task)

    # Process in parallel with concurrency limit
    semaphore = asyncio.Semaphore(self.max_workers * 2)

    async def limited_task(task):
        async with semaphore:
            return await task

    limited_tasks = [limited_task(task) for task in tasks]
    results = await asyncio.gather(*limited_tasks, return_exceptions=True)

    return results
```

#### 2.2 Streaming Processing
```python
async def stream_optimize(self, document_stream: AsyncIterator[str]) -> AsyncIterator[OptimizationResult]:
    """Stream processing for continuous document flow."""
    buffer = []
    async for doc in document_stream:
        buffer.append(doc)

        # Process when buffer is full
        if len(buffer) >= self.batch_size:
            results = await self.batch_optimize_async_parallel(buffer)
            for result in results:
                yield result
            buffer.clear()

    # Process remaining
    if buffer:
        results = await self.batch_optimize_async_parallel(buffer)
        for result in results:
            yield result
```

### Phase 3: Advanced Optimizations (30-50x speedup)

#### 3.1 Multi-Tier Caching
```python
class MultiTierCache:
    """Three-tier caching system."""

    def __init__(self):
        # L1: In-memory LRU cache (fastest)
        self.l1_cache = LRUCache(maxsize=10000)

        # L2: Shared memory cache (fast, persistent)
        self.l2_cache = SharedMemoryCache(size_mb=100)

        # L3: Disk cache (large capacity)
        self.l3_cache = DiskCache(path="cache/", size_gb=1)

    async def get(self, key: str) -> Optional[Any]:
        # Check L1
        if value := self.l1_cache.get(key):
            return value

        # Check L2
        if value := await self.l2_cache.get(key):
            self.l1_cache.set(key, value)  # Promote to L1
            return value

        # Check L3
        if value := await self.l3_cache.get(key):
            await self.l2_cache.set(key, value)  # Promote to L2
            self.l1_cache.set(key, value)  # Promote to L1
            return value

        return None
```

#### 3.2 Vectorized Operations
```python
def calculate_entropy_batch_vectorized(self, documents: List[str]) -> np.ndarray:
    """Fully vectorized entropy calculation."""
    # Tokenize all documents
    all_words = [self.tokenize(doc) for doc in documents]

    # Vectorized probability calculation
    entropies = np.zeros(len(documents))

    for i, words in enumerate(all_words):
        if not words:
            continue

        # Use NumPy for fast computation
        unique, counts = np.unique(words, return_counts=True)
        probabilities = counts / len(words)
        entropies[i] = -np.sum(probabilities * np.log2(probabilities))

    return entropies
```

#### 3.3 Process Pool for CPU-Bound Operations
```python
class ProcessPoolOptimizer:
    """Use process pool for CPU-intensive operations."""

    def __init__(self, num_processes: int = None):
        self.pool = ProcessPoolExecutor(max_workers=num_processes or cpu_count())

    async def optimize_batch_multiprocess(self, documents: List[str]) -> List[OptimizationResult]:
        """Distribute work across processes."""
        # Split documents into chunks
        chunk_size = len(documents) // self.pool._max_workers
        chunks = [documents[i:i+chunk_size] for i in range(0, len(documents), chunk_size)]

        # Process chunks in parallel processes
        futures = []
        for chunk in chunks:
            future = self.pool.submit(self._process_chunk, chunk)
            futures.append(future)

        # Gather results
        results = []
        for future in as_completed(futures):
            chunk_results = future.result()
            results.extend(chunk_results)

        return results
```

### Phase 4: Architecture Optimization

#### 4.1 Pipeline Architecture
```python
class OptimizationPipeline:
    """High-performance document processing pipeline."""

    def __init__(self):
        # Stage 1: Input queue
        self.input_queue = asyncio.Queue(maxsize=10000)

        # Stage 2: Preprocessing workers
        self.preprocessors = [PreprocessWorker() for _ in range(4)]

        # Stage 3: Optimization workers
        self.optimizers = [OptimizationWorker() for _ in range(16)]

        # Stage 4: Output queue
        self.output_queue = asyncio.Queue(maxsize=10000)

    async def process(self):
        """Run the pipeline."""
        # Start all workers
        tasks = []

        # Preprocessing stage
        for worker in self.preprocessors:
            task = asyncio.create_task(worker.run(self.input_queue, self.optimization_queue))
            tasks.append(task)

        # Optimization stage
        for worker in self.optimizers:
            task = asyncio.create_task(worker.run(self.optimization_queue, self.output_queue))
            tasks.append(task)

        # Run until cancelled
        await asyncio.gather(*tasks)
```

#### 4.2 Intelligent Batching
```python
class AdaptiveBatcher:
    """Dynamically adjust batch size based on system load."""

    def __init__(self):
        self.min_batch = 100
        self.max_batch = 2000
        self.current_batch = 500
        self.target_latency = 100  # ms

    def adjust_batch_size(self, last_latency: float, throughput: float):
        """Adjust batch size based on performance."""
        if last_latency > self.target_latency * 1.2:
            # Reduce batch size if latency too high
            self.current_batch = max(self.min_batch, int(self.current_batch * 0.8))
        elif last_latency < self.target_latency * 0.8 and throughput < 4000:
            # Increase batch size if latency low and throughput not at target
            self.current_batch = min(self.max_batch, int(self.current_batch * 1.2))

        return self.current_batch
```

## Implementation Plan

### Step 1: Quick Optimizations (Day 1)
- [ ] Increase worker count to 16
- [ ] Increase batch size to 1000
- [ ] Compile all regex patterns
- [ ] Optimize cache key generation

**Expected Impact**: 2-3x speedup (7,000-10,000 docs/minute)

### Step 2: Async Implementation (Day 2-3)
- [ ] Implement async LLM adapter methods
- [ ] Convert optimization pipeline to async
- [ ] Add streaming support
- [ ] Implement concurrent batch processing

**Expected Impact**: 10-20x speedup (35,000-70,000 docs/minute)

### Step 3: Advanced Caching (Day 4)
- [ ] Implement multi-tier cache
- [ ] Add shared memory cache
- [ ] Implement disk cache for persistence
- [ ] Add cache preloading

**Expected Impact**: Additional 2x speedup (70,000-140,000 docs/minute)

### Step 4: Architecture Optimization (Day 5-6)
- [ ] Implement pipeline architecture
- [ ] Add process pool for CPU operations
- [ ] Implement adaptive batching
- [ ] Add load balancing

**Expected Impact**: Final 2x speedup (140,000-280,000 docs/minute)

## Performance Validation

### Benchmarks to Run

1. **Micro-benchmarks**:
   - Entropy calculation: Target 10,000+ docs/sec
   - Quality measurement: Target 10,000+ docs/sec
   - Cache hit rate: Target >90%

2. **Integration benchmarks**:
   - Single document optimization: Target <25ms
   - Batch optimization (1000 docs): Target <15 seconds
   - Streaming throughput: Target 4,000+ docs/sec

3. **Stress tests**:
   - Sustained load: 248K docs/minute for 10 minutes
   - Memory stability: <1GB growth over 1 hour
   - CPU utilization: <80% average

### Success Criteria

- ✅ Achieve 248,000 documents/minute throughput
- ✅ Maintain <1% error rate
- ✅ Keep memory usage <2GB for 10,000 document batch
- ✅ Maintain 85%+ test coverage
- ✅ Pass all security validations

## Risk Mitigation

### Potential Risks

1. **LLM Rate Limits**:
   - Mitigation: Implement exponential backoff and request queuing

2. **Memory Overflow**:
   - Mitigation: Implement memory monitoring and automatic batch size reduction

3. **Quality Degradation**:
   - Mitigation: Add quality gates and automatic rollback if quality drops

4. **Concurrency Issues**:
   - Mitigation: Use proper locking and async-safe data structures

## Conclusion

The performance analysis shows that the core mathematical operations (Shannon entropy, quality measurement) already exceed the target performance. The bottleneck is in the optimization pipeline, specifically the LLM calls.

By implementing the four-phase optimization strategy:
1. Quick wins (2-3x)
2. Async processing (10-20x)
3. Advanced caching (2x)
4. Architecture optimization (2x)

We can achieve the cumulative 68.2x speedup needed to reach 248,000 documents/minute.

The implementation is low-risk because:
- Core algorithms are already optimal
- Changes are primarily architectural
- Each phase can be validated independently
- Rollback is possible at any stage
