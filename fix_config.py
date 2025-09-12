#!/usr/bin/env python3
"""
Fix and test configuration loading
"""

import sys
import os
import yaml
from pathlib import Path

sys.path.insert(0, '/Users/etherealogic/Dev/DocDevAI-v3.0.0')

def check_config_file():
    """Check the actual content of the config file"""
    print("=== Checking Configuration File ===")
    
    config_file = Path.home() / ".devdocai.yml"
    print(f"Config file path: {config_file}")
    print(f"Config file exists: {config_file.exists()}")
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            content = f.read()
            print("Raw file content:")
            print(content)
            print("\n" + "="*50 + "\n")
            
        # Parse YAML
        try:
            data = yaml.safe_load(content)
            print("Parsed YAML data:")
            print(data)
            
            # Check LLM section
            if 'llm' in data:
                llm_section = data['llm']
                print(f"\nLLM section: {llm_section}")
                print(f"API key: {llm_section.get('api_key', 'NOT FOUND')}")
            else:
                print("No 'llm' section found in config!")
                
        except Exception as e:
            print(f"Error parsing YAML: {e}")

def test_config_loading():
    """Test the configuration system"""
    print("=== Testing Configuration Loading ===")
    
    # Clear environment variables
    old_env = {}
    for key in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY']:
        old_env[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]
    
    try:
        from devdocai.core.config import ConfigurationManager
        
        config = ConfigurationManager()
        
        print(f"Config file path: {config.config_file}")
        print(f"Config file exists: {config.config_file.exists()}")
        
        # Test LLM config
        llm_config = config.get_llm_config()
        print(f"LLM config: {llm_config}")
        print(f"LLM provider: {llm_config.provider}")
        print(f"LLM api_key: {llm_config.api_key}")
        
        # Test get_api_key method
        api_key = config.get_api_key("openai")
        print(f"get_api_key('openai'): {api_key}")
        
        # Check environment variables
        print(f"OPENAI_API_KEY env: {os.getenv('OPENAI_API_KEY')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore environment variables
        for key, value in old_env.items():
            if value is not None:
                os.environ[key] = value

def test_direct_yaml_load():
    """Test loading YAML directly"""
    print("=== Testing Direct YAML Load ===")
    
    config_file = Path("/Users/etherealogic/.devdocai.yml")  # Use absolute path
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
                
            print("Direct YAML load successful:")
            print(f"Full data: {data}")
            
            if 'llm' in data:
                llm_data = data['llm']
                api_key = llm_data.get('api_key')
                print(f"Direct API key: {api_key}")
                print(f"API key length: {len(api_key) if api_key else 0}")
                
                if api_key and len(api_key) > 20:
                    print("✅ API key looks valid!")
                else:
                    print("❌ API key missing or too short")
            else:
                print("❌ No LLM section found")
                
        except Exception as e:
            print(f"Error loading YAML: {e}")
    else:
        print("❌ Config file not found")

if __name__ == "__main__":
    print("Configuration Debug Script")
    print("=" * 60)
    
    check_config_file()
    print("\n" + "=" * 60)
    
    test_direct_yaml_load()
    print("\n" + "=" * 60)
    
    test_config_loading()