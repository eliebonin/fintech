// Loopback-only companion to run_fx_forward_e2e.py. No operating cookies/cache.
const next = require('../apps/ops-console/node_modules/next');
const path = require('path');
const app = next({ dev: true, dir: path.resolve(__dirname, '../apps/ops-console'), hostname: 'fx-e2e.localhost', port: 3009 });
app.prepare().then(() => require('http').createServer(app.getRequestHandler()).listen(3009, '127.0.0.1'));
