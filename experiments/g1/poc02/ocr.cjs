const { createHash } = require('node:crypto');
const { readFileSync } = require('node:fs');
const path = require('node:path');

async function main() {
  const [directory, ...images] = process.argv.slice(2);
  if (!directory || images.length === 0) {
    throw new Error('Usage: node ocr.cjs <tool-directory> <image...>');
  }
  const modules = path.join(directory, 'node_modules');
  const engine = path.join(modules, 'tesseract.js');
  const core = path.join(modules, 'tesseract.js-core');
  const language = path.join(modules, '@tesseract.js-data', 'vie');
  const model = path.join(language, '4.0.0_best_int');
  const { createWorker, PSM } = require(engine);
  const worker = await createWorker('vie', 1, {
    langPath: model,
    cacheMethod: 'none',
  });
  try {
    await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT });
    const observations = [];
    for (const image of images) {
      const { data } = await worker.recognize(image);
      observations.push({ text: data.text, confidence: data.confidence });
    }
    process.stdout.write(JSON.stringify({
      config: {
        node: process.version,
        tesseract: require(path.join(engine, 'package.json')).version,
        core: require(path.join(core, 'package.json')).version,
        language: 'vie',
        languagePackage: require(path.join(language, 'package.json')).version,
        model: path.basename(model),
        modelSha256: createHash('sha256').update(readFileSync(path.join(model, 'vie.traineddata.gz'))).digest('hex'),
        pageSegmentation: 'SPARSE_TEXT',
      },
      images: observations,
    }));
  } finally {
    await worker.terminate();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
