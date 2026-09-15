#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${DEPTHWIZARD_URL:-http://localhost:5173}"
TEST_IMAGE="${1:-../zaalima.jpeg}"

playwright-cli open "$BASE_URL"
playwright-cli run-code "async page => {
  const errors = [];
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', error => errors.push(error.message));
  await page.locator('input[type=file]').setInputFiles('$TEST_IMAGE');
  await page.getByText('CNN boundary refinement active', { exact: false }).waitFor({ state: 'visible', timeout: 30000 });
  const presentationToggle = page.getByRole('button', { name: 'Toggle presentation view' });
  const presentationMode = await presentationToggle.getAttribute('aria-pressed');
  const topViewToggle = page.getByRole('button', { name: 'Top view' });
  await topViewToggle.click();
  const topViewActive = await topViewToggle.getAttribute('aria-pressed');
  await page.waitForTimeout(750);
  await page.screenshot({ path: '../.scratch/render-review-zaalima-ticket04.png', scale: 'device', type: 'png' });
  const treeToggle = page.getByRole('button', { name: /Trees Bounded tree geometry/ });
  const before = await treeToggle.getAttribute('aria-pressed');
  await treeToggle.click();
  const after = await treeToggle.getAttribute('aria-pressed');
  const buildingNote = await page.getByText('Buildings: GAMUS semantic mask', { exact: false }).count();
  if (presentationMode !== 'true' || topViewActive !== 'true' || before !== 'true' || after !== 'false' || !buildingNote || errors.length) {
    throw new Error(JSON.stringify({ presentationMode, topViewActive, before, after, buildingNote, errors }));
  }
  return JSON.stringify({ upload: true, inference: true, presentationMode: true, topView: true, layerToggle: true, geometryReport: buildingNote > 0, consoleErrors: errors.length });
}"
playwright-cli console error
