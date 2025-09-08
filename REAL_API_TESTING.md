# Real API Testing Guide for DevDocAI v3.0.0

## Quick Start

### Setup
```bash
# 1. Create/activate venv
python3 -m venv .venv && source .venv/bin/activate

# 2. Install package + provider SDKs
pip install -U pip && pip install -e . && pip install openai anthropic google-generativeai

# 3. Add keys to .env in project root:
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=your-key-here  
GOOGLE_API_KEY=your-key-here
# (or GEMINI_API_KEY=... - both work)

# 4. Verify imports
python -c "import devdocai.core.config, devdocai.intelligence.llm_adapter"
```

### Run Tests

```bash
# Interactive menu (recommended)
./scripts/test_real_api.sh
# Options: 1=all, 2=specific, 3=perf, 4=verbose

# Direct pytest  
REAL_API_TESTING=1 python -m pytest tests/integration/test_real_api.py -v -s

# Non-interactive "run all"
printf "1\n" | ./scripts/test_real_api.sh
```

## What You'll See

```
✅ OpenAI Response: 4
✅ Claude Response: 4  
✅ Gemini Response: 4
✅ Cost tracked: $0.000234
✅ Rate limiting working correctly
✅ Response time: 1.23s
```

**Test Behavior:**
- Tests skip gracefully if provider key is missing or SDK isn't installed
- Real API calls are made with minimal usage and cost tracking
- All costs are reported during test execution

## Recent Enhancements (Codex Integration)

### Configuration Improvements
- **Auto .env loading**: `python-dotenv` automatically loads `.env` file
- **Flexible key names**: Supports `GEMINI_API_KEY` or `GOOGLE_API_KEY`  
- **Provider aliases**: `anthropic`/`claude`, `gemini`/`google`
- **No manual exports**: Keys loaded automatically from `.env`

### LLM Adapter Enhancements
- **ProviderType enum**: `OPENAI`, `CLAUDE`, `GEMINI`, `LOCAL`
- **Test-friendly API**: `generate()` returns text when `REAL_API_TESTING=1`
- **Cost helpers**: `get_total_cost()` and `reset_costs()`
- **Rate limiting**: Configurable via `rate_limit_requests_per_minute=`

### Design Compliance Maintained
- **SDD 5.4**: Multi-provider routing + cost tracking preserved
- **SDD 6**: Cost management exposed without changing core accounting  
- **SDD 7.1**: Security (rate limiting, request signing, audit logging) intact

## Cost & Usage Notes

- **Real API Calls**: These tests make actual API calls and will consume credits
- **Minimal Usage**: Each test uses very small prompts (~10 tokens max)
- **Cost Tracking**: All usage is measured and reported
- **Provider SDKs Required**: `openai`, `anthropic`, `google-generativeai`

## Troubleshooting

### Import Errors
```bash
# Missing provider SDKs
pip install openai anthropic google-generativeai

# Missing devdocai package
pip install -e .
```

### Authentication Errors  
```bash
# Check .env file exists and has keys
cat .env

# Verify keys are loaded
python -c "from devdocai.core.config import ConfigurationManager; c=ConfigurationManager(); print(bool(c.get_api_key('openai')))"
```

### Test Skipping
- Tests automatically skip if API keys are missing
- Use `REAL_API_TESTING=1` to enable integration tests
- Provider SDKs must be installed for each provider tested

## Files Created/Modified

### New Files
- `tests/integration/test_real_api.py` - Real API integration tests
- `tests/integration/__init__.py` - Integration test package
- `scripts/test_real_api.sh` - Interactive test runner
- `REAL_API_TESTING.md` - This documentation

### Modified Files (by Codex)
- `devdocai/intelligence/llm_adapter.py` - Added test-friendly API and ProviderType enum
- `devdocai/core/config.py` - Auto .env loading and flexible key naming
- `.gitignore` - Protection for `.env` and secret files

## Security Notes

- `.env` file is protected by `.gitignore` (won't be committed)
- API keys are never logged or stored in test output
- Rate limiting prevents runaway API usage
- Tests disabled by default (require `REAL_API_TESTING=1`)
- All API calls are authenticated and tracked