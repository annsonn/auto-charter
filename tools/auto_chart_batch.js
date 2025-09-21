#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');
const AdmZip = require('adm-zip');

function getArg(flag, defaultValue) {
  const index = process.argv.indexOf(flag);
  if (index !== -1 && index + 1 < process.argv.length) {
    return process.argv[index + 1];
  }
  return defaultValue;
}

const inputRoot = path.resolve(getArg('--input', process.env.INPUT_DIR || '/work/out'));
const outputRoot = path.resolve(getArg('--output', process.env.OUTPUT_DIR || '/work/charts'));
const midiChRoot = path.resolve(getArg('--midi-ch-root', process.env.MIDI_CH_ROOT || '/app/midi-ch/auto'));

async function findMergedFiles(dir) {
  let results = [];
  const entries = await fs.promises.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results = results.concat(await findMergedFiles(fullPath));
    } else if (entry.isFile() && entry.name.toLowerCase() === 'merged.mid') {
      results.push(fullPath);
    }
  }
  return results;
}

async function convertWithPuppeteer(browser, midiPath) {
  const page = await browser.newPage();
  page.setDefaultTimeout(0);

  let resolved = false;
  let resolveChart;
  const chartPromise = new Promise((resolve) => {
    resolveChart = resolve;
  });

  await page.exposeFunction('__chartSave', ({ filename, bytes }) => {
    if (resolved) {
      return;
    }
    resolved = true;
    resolveChart({ filename, buffer: Buffer.from(bytes) });
  });

  await page.evaluateOnNewDocument(() => {
    window.saveAs = (blob, filename) => {
      blob.arrayBuffer().then((buffer) => {
        const bytes = Array.from(new Uint8Array(buffer));
        window.__chartSave({ filename, bytes });
      });
    };
  });

  const url = `file://${midiChRoot.replace(/\\/g, '/')}/index.html`;
  await page.goto(url, { waitUntil: 'networkidle0' });

  const fileInput = await page.$('input[type="file"]');
  if (!fileInput) {
    throw new Error('Could not locate file input on MIDI-CH auto page.');
  }

  const waitForChart = Promise.race([
    chartPromise,
    new Promise((_, reject) => setTimeout(() => reject(new Error('Timed out waiting for MIDI-CH to produce output.')), 120000))
  ]);

  await fileInput.uploadFile(midiPath);

  const result = await waitForChart;
  await page.close();
  return result;
}

async function extractToCharts(buffer, filename, destinationDir, fallbackName) {
  if (filename.toLowerCase().endsWith('.zip')) {
    const zip = new AdmZip(buffer);
    zip.getEntries().forEach((entry) => {
      const targetPath = path.join(destinationDir, entry.entryName);
      if (entry.isDirectory) {
        fs.mkdirSync(targetPath, { recursive: true });
      } else {
        fs.mkdirSync(path.dirname(targetPath), { recursive: true });
        fs.writeFileSync(targetPath, entry.getData());
      }
    });
    return;
  }

  const finalName = filename || `${fallbackName}.chart`;
  const target = path.join(destinationDir, finalName);
  await fs.promises.mkdir(path.dirname(target), { recursive: true });
  await fs.promises.writeFile(target, buffer);
}

function deriveMetadataFromName(name) {
  const sanitized = name.trim();
  if (!sanitized) {
    return { artist: '', title: '' };
  }
  const separatorIndex = sanitized.indexOf(' - ');
  if (separatorIndex === -1) {
    return { artist: '', title: sanitized };
  }
  const artist = sanitized.slice(0, separatorIndex).trim();
  const title = sanitized.slice(separatorIndex + 3).trim() || sanitized;
  return { artist, title };
}

async function applyMetadata(destinationDir, { artist, title }) {
  const tasks = [];
  if (title || artist) {
    tasks.push(updateSongIni(path.join(destinationDir, 'song.ini'), artist, title));
    tasks.push(updateChartMetadata(path.join(destinationDir, 'notes.chart'), artist, title));
  }
  await Promise.allSettled(tasks);
}

async function updateSongIni(iniPath, artist, title) {
  try {
    let content = await fs.promises.readFile(iniPath, 'utf8');
    content = setIniValue(content, 'name', title || null);
    content = setIniValue(content, 'artist', artist || null);
    if (content !== null) {
      await fs.promises.writeFile(iniPath, content, 'utf8');
    }
  } catch (err) {
    if (err.code !== 'ENOENT') {
      console.warn(`Could not update song.ini at ${iniPath}: ${err.message}`);
    }
  }
}

function setIniValue(content, key, value) {
  if (!value) {
    return content;
  }
  const lineEnding = content.includes('\r\n') ? '\r\n' : '\n';
  const regex = new RegExp(`(^\\s*${key}\\s*=).*$`, 'mi');
  if (regex.test(content)) {
    return content.replace(regex, `$1 ${value}`);
  }
  const insertionPoint = content.indexOf('[Song]');
  if (insertionPoint === -1) {
    return `${content}${lineEnding}${key} = ${value}${lineEnding}`;
  }
  const afterHeaderIndex = content.indexOf(lineEnding, insertionPoint);
  if (afterHeaderIndex === -1) {
    return `${content}${lineEnding}${key} = ${value}${lineEnding}`;
  }
  return `${content.slice(0, afterHeaderIndex + lineEnding.length)}${key} = ${value}${lineEnding}${content.slice(afterHeaderIndex + lineEnding.length)}`;
}

async function updateChartMetadata(chartPath, artist, title) {
  try {
    let content = await fs.promises.readFile(chartPath, 'utf8');
    if (title) {
      const nameRegex = /(Name\s*=\s*")(.*?)(")/;
      if (nameRegex.test(content)) {
        content = content.replace(nameRegex, `$1${escapeChartValue(title)}$3`);
      }
    }
    if (artist) {
      const artistRegex = /(Artist\s*=\s*")(.*?)(")/;
      if (artistRegex.test(content)) {
        content = content.replace(artistRegex, `$1${escapeChartValue(artist)}$3`);
      } else {
        content = content.replace(/(Name\s*=\s*".*"\s*\n)/, `$1  Artist = "${escapeChartValue(artist)}"\n`);
      }
    }
    await fs.promises.writeFile(chartPath, content, 'utf8');
  } catch (err) {
    if (err.code !== 'ENOENT') {
      console.warn(`Could not update notes.chart at ${chartPath}: ${err.message}`);
    }
  }
}

function escapeChartValue(value) {
  return value.replace(/"/g, '\\"');
}

(async () => {
  if (fs.existsSync(outputRoot)) {
    await fs.promises.rm(outputRoot, { recursive: true, force: true });
  }
  await fs.promises.mkdir(outputRoot, { recursive: true });

  const mergedFiles = fs.existsSync(inputRoot) ? await findMergedFiles(inputRoot) : [];
  if (mergedFiles.length === 0) {
    console.error(`No merged.mid files found under ${inputRoot}`);
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });

  try {
    for (const midiPath of mergedFiles) {
      const relativeDir = path.relative(inputRoot, path.dirname(midiPath));
      const songDir = relativeDir === '' ? path.basename(path.dirname(midiPath)) : relativeDir.split(path.sep)[0];
      const chartDestination = path.join(outputRoot, songDir);
      await fs.promises.mkdir(chartDestination, { recursive: true });

      console.log(`Processing ${midiPath} -> ${chartDestination}`);
      const { filename, buffer } = await convertWithPuppeteer(browser, midiPath);
      const fallback = path.basename(midiPath, path.extname(midiPath));
      await extractToCharts(buffer, filename, chartDestination, fallback);
      await fs.promises.copyFile(midiPath, path.join(chartDestination, 'notes.mid'));

      const metadata = deriveMetadataFromName(songDir);
      await applyMetadata(chartDestination, metadata);
    }
  } finally {
    await browser.close();
  }
})();

