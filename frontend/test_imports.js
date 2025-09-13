// Test import isolation
console.log('Testing imports...');

try {
  console.log('1. Testing api import...');
  const apiModule = await import('./src/services/api.ts');
  console.log('✅ API module loaded:', Object.keys(apiModule));
} catch (error) {
  console.log('❌ API module failed:', error.message);
}

try {
  console.log('2. Testing configuration service import...');
  const configModule = await import('./src/services/modules/configuration.ts');
  console.log('✅ Configuration module loaded:', Object.keys(configModule));
} catch (error) {
  console.log('❌ Configuration module failed:', error.message);
}

try {
  console.log('3. Testing services index import...');
  const servicesModule = await import('./src/services/index.ts');
  console.log('✅ Services index loaded:', Object.keys(servicesModule));
} catch (error) {
  console.log('❌ Services index failed:', error.message);
}