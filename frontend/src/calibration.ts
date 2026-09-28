import type { CalibrationMetadata } from "./types";

function appendGeoTiffCalibration(formData: FormData, filename: string, options: { enabled: boolean; elevation: string; provenance: string }) {
  if (!/\.tiff?$/i.test(filename)) return;
  formData.append("calibrate_geotiff", String(options.enabled));
  if (options.enabled && options.elevation.trim()) formData.append("ground_elevation", options.elevation.trim());
  if (options.enabled && options.elevation.trim() && options.provenance.trim()) formData.append("ground_elevation_provenance", options.provenance.trim());
}

function dsmDownloadUrl(resultType: "estimated_ndsm" | "metric_dsm", url?: string | null) {
  return resultType === "metric_dsm" ? url ?? null : null;
}

function describeCalibration(heightReference: "relative" | "absolute", calibration?: CalibrationMetadata) {
  const calibrated = heightReference === "absolute";
  return {
    reference: calibrated ? "Calibrated DSM · meters" : "Estimated nDSM · relative meters",
    fit: calibrated
      ? `Calibration indicator (fit consistency and evidence coverage): ${calibration?.confidence == null ? "—" : `${(calibration.confidence * 100).toFixed(0)}%`} · ground-fit residual ${calibration?.residualError == null ? "—" : `${calibration.residualError.toFixed(2)} m`}.`
      : `Calibration unavailable: ${(calibration?.status ?? "not_applicable").replaceAll("_", " ")}. Heights remain relative estimates.`,
    accuracy: calibrated
      ? calibration?.groundElevationProvenance
        ? `User-reported elevation source: ${calibration.groundElevationProvenance}. Provenance is not independently verified; real-world accuracy is unverified.`
        : "Real-world accuracy is unverified. Ground-fit residual measures fit consistency, not surveyed accuracy."
      : null,
  };
}

export { appendGeoTiffCalibration, describeCalibration, dsmDownloadUrl };
