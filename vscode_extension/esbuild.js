const esbuild = require('esbuild');

const production = process.argv.includes('--production');
const watch = process.argv.includes('--watch');

const ctx = {
  entryPoints: ['src/extension.ts'],
  bundle: true,
  format: 'cjs',
  platform: 'node',
  target: 'node18',
  outfile: 'dist/extension.js',
  external: ['vscode'],
  sourcemap: !production,
  minify: production,
  logLevel: 'info',
};

(async () => {
  if (watch) {
    const context = await esbuild.context(ctx);
    await context.watch();
  } else {
    await esbuild.build(ctx);
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
