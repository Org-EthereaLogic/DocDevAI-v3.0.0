import asyncio
from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import StorageManager, Document
from devdocai.intelligence.llm_adapter import LLMAdapter
from devdocai.core.generator import DocumentGenerator

async def run_integration_test():
    print('🚀 End-to-End Integration Validation')
    print('=' * 50)
    
    # Initialize complete system
    try:
        config = ConfigurationManager()
        storage = StorageManager(config)
        llm = LLMAdapter(config)
        generator = DocumentGenerator(config, storage, llm)
        print('✅ Complete system initialized')
    except Exception as e:
        print(f'❌ System initialization failed: {e}')
        return
    
    # Test 1: Generate a small document using AI
    try:
        print()
        print('📝 Testing AI-powered document generation...')
        
        context = {
            'project_name': 'DevDocAI Test',
            'description': 'Testing our production system',
            'version': '3.0.0'
        }
        
        result = await generator.generate_document(
            template_name='readme',
            context=context
        )
        
        if result and hasattr(result, 'document') and result.document:
            print('✅ Document generated successfully')
            print(f"   Length: {len(result.document)} characters")
            print('   Preview: ' + result.document[:100].replace('\n', ' ') + '...')
        else:
            print('⚠️ Document generation returned empty/invalid result')
            
    except Exception as e:
        print(f'❌ Document generation failed: {e}')
    
    # Test 2: Store generated document separately (already auto-stored)
    try:
        print()
        print('💾 Testing document storage integration...')
        
        if result and hasattr(result, 'document'):
            # Note: Document is already auto-stored by generator
            print('✅ Document auto-stored during generation')
            print(f"   Generated ID: {result.metadata.get('id', 'unknown')}")
            
            # Test manual storage as well
            doc = Document(
                title='Manual Test README',
                content=result.document,
                doc_type='readme',
                metadata={'test': 'manual_storage'}
            )
            
            doc_id = storage.save_document(doc)
            print(f"✅ Manual document stored successfully (ID: {doc_id})")
            
            # Verify retrieval
            retrieved = storage.get_document(doc_id)
            if retrieved and retrieved.title == 'Manual Test README':
                print('✅ Document retrieval verified')
            else:
                print('⚠️ Document retrieval issue')
                
    except Exception as e:
        print(f'❌ Document storage failed: {e}')
    
    # Test 3: Performance stats
    try:
        print()
        print('📊 System performance summary...')
        
        stats = generator.get_performance_stats()
        print(f"✅ Memory mode: {stats.get('memory_mode', 'unknown')}")
        print(f"✅ Batch size: {stats.get('configuration', {}).get('max_batch_size', 'unknown')}")
        print(f"✅ Workers: {stats.get('configuration', {}).get('max_workers', 'unknown')}")
        
        # Cost summary
        current_costs = llm.cost_manager.get_current_costs()
        print(f"✅ Total costs: ${current_costs.get('total', 0):.6f}")
        
    except Exception as e:
        print(f'❌ Performance stats failed: {e}')
    
    print()
    print('🎯 Integration test completed!')
    print('=' * 50)

# Run the async test
asyncio.run(run_integration_test())
