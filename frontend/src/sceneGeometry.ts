type BuildingLayout = {
  wallBaseY: number;
  wallCenterY: number;
  roofBaseY: number;
};

function getBuildingLayout(height: number): BuildingLayout {
  const safeHeight = Math.max(height, 0);
  return {
    wallBaseY: 0,
    wallCenterY: safeHeight / 2,
    roofBaseY: safeHeight,
  };
}

export type { BuildingLayout };
export { getBuildingLayout };
