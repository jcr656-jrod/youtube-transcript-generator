// Railway.app frontend configuration
const API_BASE_URL = window.location.hostname.includes('localhost')
  ? 'http://localhost:8000'
  : `${window.location.protocol}//${window.location.hostname}:${window.location.port || 443}`;

console.log('API Base URL:', API_BASE_URL);
