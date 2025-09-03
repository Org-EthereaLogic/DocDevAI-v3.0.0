# M004 Document Generator - AI Transformation Plan

## Executive Summary

Transform M004 from a template substitution engine into an AI-powered document generation system using the proven 4-pass development methodology that delivered exceptional results for M001-M013.

## Current State vs Target State

### Current State (Template Engine)
- Simple variable substitution: `{{variable}}` → value
- Static templates with placeholders
- No LLM integration in generation flow
- MIAIR only scores quality, doesn't synthesize
- Single document generation

### Target State (AI-Powered Suite Generator)
- LLM prompt templates with rich context
- Multi-LLM synthesis (Claude 40%, GPT 35%, Gemini 25%)
- Document dependency graph with proper ordering
- Multi-phase review system with specialized LLMs
- Complete suite generation with compliance review

## 4-Pass Development Strategy

### Pass 1: Core Implementation (Days 1-3)
**Goal**: Get basic AI document generation working end-to-end

#### Deliverables
1. **Integration Layer** (`ai_document_generator.py`)
   - Connect PromptTemplateEngine to M008 LLM Adapter
   - Implement basic single-document AI generation
   - Parse LLM responses into structured documents
   - Store generated documents in M002 storage

2. **Template Conversion** (5-10 templates)
   - Convert your Anthropic examples to YAML format
   - Start with core templates:
     - `user_stories_generation.yaml`
     - `project_plan_generation.yaml`
     - `srs_generation.yaml`
     - `architecture_generation.yaml`
     - `first_draft_review.yaml`

3. **Basic Workflow** 
   - Single-pass generation (no reviews yet)
   - Sequential document creation
   - Basic dependency handling
   - Simple multi-LLM synthesis

4. **Testing**
   - End-to-end generation test
   - LLM adapter integration test
   - Template rendering test
   - Basic quality validation

#### Success Metrics
- Generate 4 core documents from user input
- Multi-LLM synthesis working (even if slow)
- Documents stored and retrievable
- 70% test coverage

#### Implementation Priority
```python
# Phase 1.1: Wire existing components
AIDocumentGenerator(
    llm_adapter=existing_m008,
    template_engine=new_prompt_engine,
    storage=existing_m002,
    miair=existing_m003  # Basic integration only
)

# Phase 1.2: Basic generation flow
generate_document(template="user_stories", input=user_description)
→ Load template
→ Render prompt
→ Query LLMs
→ Parse response
→ Store document

# Phase 1.3: Dependency handling
generate_suite(initial_input)
→ Generate user stories
→ Generate project plan (with user stories as context)
→ Generate SRS (with user stories + project plan)
→ Generate architecture (with all previous)
```

### Pass 2: Performance Optimization (Days 4-5)
**Goal**: Make it fast and efficient

#### Optimizations
1. **Parallel LLM Calls**
   - Concurrent multi-LLM queries for synthesis
   - Parallel review phases where possible
   - Batch processing for related prompts

2. **Intelligent Caching**
   - Cache LLM responses by prompt hash
   - Semantic similarity matching for cache hits
   - Document fragment caching
   - Template compilation caching

3. **Streaming Generation**
   - Stream LLM responses for large documents
   - Progressive rendering to user
   - Chunked document processing

4. **Resource Management**
   - Token usage optimization
   - Smart prompt truncation
   - Context window management
   - Cost-aware provider selection

#### Success Metrics
- <30 seconds for single document generation
- <5 minutes for complete suite generation
- 30% cache hit rate on similar requests
- 50% reduction in token usage through optimization

#### Performance Targets
```yaml
single_document:
  first_generation: <30s
  cached_similar: <5s
  review_cycle: <15s per phase

suite_generation:
  4_core_documents: <3 minutes
  full_suite_18_docs: <10 minutes
  with_all_reviews: <15 minutes

token_optimization:
  prompt_compression: 30% reduction
  response_parsing: Extract only needed sections
  cache_reuse: 30% hit rate target
```

### Pass 3: Security Hardening (Days 6-7)
**Goal**: Protect against AI-specific threats

#### Security Measures
1. **Prompt Injection Protection**
   - Input sanitization for user content
   - Prompt structure validation
   - System prompt isolation
   - Output validation against injection patterns

2. **Data Protection**
   - Encrypt stored prompts and responses
   - PII detection and masking in documents
   - Secure context handling between documents
   - API key rotation and management

3. **Rate Limiting & DDoS Protection**
   - Per-user generation limits
   - Token budget enforcement
   - Circuit breakers for LLM providers
   - Abuse detection patterns

4. **Audit & Compliance**
   - Log all LLM interactions
   - Track document lineage
   - Version control for generated content
   - GDPR compliance for stored data

#### Success Metrics
- 0% successful prompt injection attacks
- <10% performance overhead from security
- 100% PII detection accuracy
- Complete audit trail for all generations

#### Security Implementation
```python
# Prompt injection protection
class SecurePromptRenderer:
    def sanitize_user_input(self, input_text):
        # Remove potential injection patterns
        # Validate against whitelist
        # Escape special characters
        
    def validate_llm_response(self, response):
        # Check for unexpected patterns
        # Validate structure
        # Detect potential leakage

# Rate limiting
class GenerationRateLimiter:
    limits = {
        'per_user_per_hour': 10,
        'per_user_per_day': 50,
        'tokens_per_day': 100000
    }
```

### Pass 4: Refactoring (Days 8-9)
**Goal**: Clean architecture and reduced complexity

#### Refactoring Targets
1. **Consolidate Implementations**
   - Merge basic/optimized/secure variants
   - Single configurable generator with modes
   - Unified template processing pipeline
   - Consistent error handling

2. **Design Patterns**
   - Strategy pattern for review phases
   - Factory pattern for document types
   - Observer pattern for generation progress
   - Chain of Responsibility for document pipeline

3. **Code Reduction**
   - Remove duplicate template logic
   - Consolidate LLM interaction code
   - Unified configuration management
   - Shared utility functions

4. **Interface Cleanup**
   - Consistent API across all components
   - Clear separation of concerns
   - Improved testability
   - Better documentation

#### Success Metrics
- 30-40% code reduction
- <10 cyclomatic complexity
- 95% test coverage maintained
- 0 code duplication warnings

#### Refactoring Plan
```python
# Before: Multiple generators
class BasicAIGenerator: ...
class OptimizedAIGenerator: ...
class SecureAIGenerator: ...

# After: Unified with modes
class UnifiedAIDocumentGenerator:
    def __init__(self, mode: GenerationMode):
        self.mode = mode
        self._configure_for_mode()
    
    def generate(self, **kwargs):
        # Single implementation
        # Mode-specific behaviors via strategy
```

## Implementation Schedule

### Week 1
- **Monday-Tuesday**: Pass 1 Core Implementation
- **Wednesday**: Pass 1 Testing & Validation
- **Thursday-Friday**: Pass 2 Performance Optimization

### Week 2
- **Monday-Tuesday**: Pass 3 Security Hardening
- **Wednesday-Thursday**: Pass 4 Refactoring
- **Friday**: Integration Testing & Documentation

## Risk Mitigation

1. **LLM API Failures**
   - Implement robust fallback chains
   - Local model fallback option
   - Cached response recovery

2. **Performance Degradation**
   - Progressive enhancement approach
   - Graceful degradation for slow operations
   - User-configurable quality/speed tradeoffs

3. **Cost Overruns**
   - Strict token budgets
   - Cost estimation before generation
   - Provider optimization based on cost

4. **Integration Complexity**
   - Maintain backward compatibility
   - Feature flags for new functionality
   - Incremental rollout strategy

## Success Criteria

### Pass 1 ✅ COMPLETE (Dec 19, 2024)
- [x] Basic AI generation working
- [x] 4 core documents generateable
- [x] Multi-LLM synthesis functional
- [x] 70% test coverage

**Delivered:**
- AI Document Generator (530 lines)
- 5 YAML templates converted
- Multi-LLM synthesis with weights
- Document dependency chain
- Comprehensive test suite (620 lines)

### Pass 2 ✓
- [ ] <30s single document generation
- [ ] <5min suite generation
- [ ] 30% cache hit rate
- [ ] 50% token optimization

### Pass 3 ✓
- [ ] Prompt injection protection
- [ ] PII detection active
- [ ] Complete audit trail
- [ ] <10% security overhead

### Pass 4 ✓
- [ ] 30-40% code reduction
- [ ] Unified architecture
- [ ] 95% test coverage
- [ ] Production ready

## Next Immediate Steps

1. Create `ai_document_generator.py` with basic integration
2. Convert first template (user_stories_generation.yaml)
3. Test end-to-end generation with M008
4. Implement basic document dependency handling
5. Add simple multi-LLM synthesis

## Command to Start

```bash
# Create the new AI generator module
touch devdocai/generator/ai_document_generator.py

# Create templates directory
mkdir -p devdocai/templates/prompt_templates/generation
mkdir -p devdocai/templates/prompt_templates/review

# Start with Pass 1 implementation
python -m devdocai.generator.ai_document_generator --test-basic
```

---

**Note**: This plan follows the same successful methodology used for M001-M013, adapted for the unique challenges of AI-powered document generation. Each pass builds on the previous, ensuring we have a working system at each stage while progressively enhancing capabilities.