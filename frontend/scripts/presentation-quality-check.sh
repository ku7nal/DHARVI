#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${DEPTHWIZARD_URL:-http://localhost:5173}"
TEST_IMAGE="${1:-../zaalima.jpeg}"
SCREENSHOT_DIR="${DEPTHWIZARD_SCREENSHOT_DIR:-$(pwd)/.scratch}"

playwright-cli open "$BASE_URL"
playwright-cli run-code "async page => {
  const errors = [];
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', error => errors.push(error.message));
  await page.locator('input[type=file]').setInputFiles('$TEST_IMAGE');
  await page.getByText('CNN boundary refinement active', { exact: false }).waitFor({ state: 'visible', timeout: 30000 });
  const presentationToggle = page.getByRole('button', { name: 'Toggle presentation view' });
  const presentationMode = await presentationToggle.getAttribute('aria-pressed');
  const isometricToggle = page.getByRole('button', { name: 'Isometric view' });
  const isometricActive = await isometricToggle.getAttribute('aria-pressed');
  const canvas = page.locator('canvas').first();
  const canvasBox = await canvas.boundingBox();
  if (!canvasBox || canvasBox.width < 100 || canvasBox.height < 100) throw new Error('render canvas is not visible');
  await page.waitForTimeout(750);
  await page.screenshot({ path: '${SCREENSHOT_DIR}/render-review-zaalima-ticket03-isometric.png', scale: 'device', type: 'png' });
  const topViewToggle = page.getByRole('button', { name: 'Top view' });
  await topViewToggle.click();
  const topViewActive = await topViewToggle.getAttribute('aria-pressed');
  await page.waitForTimeout(750);
  await page.screenshot({ path: '${SCREENSHOT_DIR}/render-review-zaalima-ticket03-top.png', scale: 'device', type: 'png' });
  const flyViewToggle = page.getByRole('button', { name: 'Fly view' });
  await flyViewToggle.click();
  const flyViewActive = await flyViewToggle.getAttribute('aria-pressed');
  await page.waitForTimeout(750);
  await page.screenshot({ path: '${SCREENSHOT_DIR}/render-review-zaalima-ticket03-fly.png', scale: 'device', type: 'png' });
  const treeToggle = page.getByRole('button', { name: /Trees Bounded tree geometry/ });
  const before = await treeToggle.getAttribute('aria-pressed');
  await treeToggle.click();
  const after = await treeToggle.getAttribute('aria-pressed');
  const buildingNote = await page.getByText('Buildings: GAMUS semantic mask', { exact: false }).count();
  if (presentationMode !== 'true' || isometricActive !== 'true' || topViewActive !== 'true' || flyViewActive !== 'true' || before !== 'true' || after !== 'false' || !buildingNote || errors.length) {
    throw new Error(JSON.stringify({ presentationMode, isometricActive, topViewActive, flyViewActive, before, after, buildingNote, canvasBox, errors }));
  }
  return JSON.stringify({ upload: true, inference: true, presentationMode: true, isometricView: true, topView: true, flyView: true, layerToggle: true, geometryReport: buildingNote > 0, canvas: canvasBox, consoleErrors: errors.length });
}"
playwright-cli console error
