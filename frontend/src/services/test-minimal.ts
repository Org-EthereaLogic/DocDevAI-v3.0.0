// Minimal test services export to isolate the issue

console.log('1. Starting minimal services test...');

try {
  console.log('2. Importing API client...');
  import { apiClient } from './api';
  console.log('3. API client imported successfully');
} catch (error) {
  console.log('❌ API client import failed:', error);
}

try {
  console.log('4. Importing configuration service...');
  import { configurationService } from './modules/configuration';
  console.log('5. Configuration service imported successfully');
} catch (error) {
  console.log('❌ Configuration service import failed:', error);
}

console.log('6. Minimal services test completed');

export { apiClient } from './api';
export { configurationService } from './modules/configuration';