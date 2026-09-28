import type { CalibrationMetadata } from "./types";

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

export { describeCalibration };
