import { useEffect, useRef, useState } from "react";

function RelocationZoneMap({ geoJson, highlightedZoneIds, currentZoneId }) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const svgRef = useRef(null);
  const dragRef = useRef(null);
  const features = Array.isArray(geoJson?.features) ? geoJson.features : [];
  const highlightedEntries = Array.from(highlightedZoneIds?.entries?.() || []);
  const highlightKey = highlightedEntries.map(([zoneId, tone]) => `${zoneId}:${tone}`).join("|");

  if (!features.length) {
    return <p className="helper-text">Taxi zone map unavailable.</p>;
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const pathItems = [];
  const zoneBounds = new Map();
  const zoneCenters = new Map();

  for (const feature of features) {
    const locationId = feature.properties.LocationID;
    const geometryType = feature.geometry?.type;
    const coordinates = feature.geometry?.coordinates || [];
    const polygons = geometryType === "Polygon" ? [coordinates] : coordinates;
    const pathSegments = [];
    let zoneMinX = Infinity;
    let zoneMinY = Infinity;
    let zoneMaxX = -Infinity;
    let zoneMaxY = -Infinity;

    for (const polygon of polygons) {
      for (const ring of polygon) {
        if (!Array.isArray(ring) || !ring.length) {
          continue;
        }

        const commands = ring.map(([x, y], index) => {
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
          zoneMinX = Math.min(zoneMinX, x);
          zoneMinY = Math.min(zoneMinY, y);
          zoneMaxX = Math.max(zoneMaxX, x);
          zoneMaxY = Math.max(zoneMaxY, y);
          const command = index === 0 ? "M" : "L";
          return `${command} ${x} ${-y}`;
        });

        pathSegments.push(`${commands.join(" ")} Z`);
      }
    }

    pathItems.push({
      id: locationId,
      zone: feature.properties.zone,
      path: pathSegments.join(" "),
      tone: highlightedZoneIds.get(locationId) || "default",
    });

    if (zoneMinX !== Infinity) {
      zoneBounds.set(locationId, {
        minX: zoneMinX,
        minY: zoneMinY,
        maxX: zoneMaxX,
        maxY: zoneMaxY,
      });
      zoneCenters.set(locationId, {
        x: zoneMinX + (zoneMaxX - zoneMinX) / 2,
        y: -(zoneMinY + (zoneMaxY - zoneMinY) / 2),
      });
    }
  }

  const width = maxX - minX || 1;
  const height = maxY - minY || 1;
  const centerX = minX + width / 2;
  const centerY = -maxY + height / 2;
  const zoomedWidth = width / zoomLevel;
  const zoomedHeight = height / zoomLevel;
  const maxPanX = Math.max(0, (width - zoomedWidth) / 2);
  const maxPanY = Math.max(0, (height - zoomedHeight) / 2);
  const constrainedPanX = Math.max(-maxPanX, Math.min(maxPanX, panOffset.x));
  const constrainedPanY = Math.max(-maxPanY, Math.min(maxPanY, panOffset.y));
  const viewBox = `${centerX - zoomedWidth / 2 + constrainedPanX} ${centerY - zoomedHeight / 2 + constrainedPanY} ${zoomedWidth} ${zoomedHeight}`;
  const currentZoneCenter = currentZoneId ? zoneCenters.get(currentZoneId) : null;

  useEffect(() => {
    if (!highlightedEntries.length) {
      return;
    }

    let focusMinX = Infinity;
    let focusMinY = Infinity;
    let focusMaxX = -Infinity;
    let focusMaxY = -Infinity;

    for (const [zoneId] of highlightedEntries) {
      const bounds = zoneBounds.get(zoneId);
      if (!bounds) {
        continue;
      }

      focusMinX = Math.min(focusMinX, bounds.minX);
      focusMinY = Math.min(focusMinY, bounds.minY);
      focusMaxX = Math.max(focusMaxX, bounds.maxX);
      focusMaxY = Math.max(focusMaxY, bounds.maxY);
    }

    if (focusMinX === Infinity) {
      return;
    }

    const focusWidth = Math.max(0.01, focusMaxX - focusMinX);
    const focusHeight = Math.max(0.01, focusMaxY - focusMinY);
    const paddedWidth = Math.min(width, focusWidth * 1.75);
    const paddedHeight = Math.min(height, focusHeight * 1.75);
    const nextZoom = Math.max(1, Math.min(8, Math.min(width / paddedWidth, height / paddedHeight)));
    const targetCenterX = focusMinX + focusWidth / 2;
    const targetCenterY = (-focusMaxY + -focusMinY) / 2;

    setZoomLevel(nextZoom);
    setPanOffset({
      x: targetCenterX - centerX,
      y: targetCenterY - centerY,
    });
  }, [centerX, centerY, height, highlightKey, width]);

  function handleZoomIn() {
    setZoomLevel((value) => Math.min(8, value * 1.35));
  }

  function handleZoomOut() {
    setZoomLevel((value) => {
      const nextValue = Math.max(1, value / 1.35);
      if (nextValue === 1) {
        setPanOffset({ x: 0, y: 0 });
      }
      return nextValue;
    });
  }

  function handleResetView() {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  }

  function handlePointerDown(event) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }

    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startPanX: constrainedPanX,
      startPanY: constrainedPanY,
      rectWidth: rect.width,
      rectHeight: rect.height,
    };

    if (zoomLevel > 1) {
      setIsDragging(true);
    }

    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event) {
    if (!dragRef.current || dragRef.current.pointerId !== event.pointerId || zoomLevel <= 1) {
      return;
    }

    const deltaX = ((event.clientX - dragRef.current.startX) * zoomedWidth) / dragRef.current.rectWidth;
    const deltaY = ((event.clientY - dragRef.current.startY) * zoomedHeight) / dragRef.current.rectHeight;
    setPanOffset({
      x: dragRef.current.startPanX - deltaX,
      y: dragRef.current.startPanY - deltaY,
    });
  }

  function handlePointerUp(event) {
    if (dragRef.current && dragRef.current.pointerId === event.pointerId) {
      dragRef.current = null;
      setIsDragging(false);
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function handleWheel(event) {
    event.preventDefault();
    event.stopPropagation();
    const direction = event.deltaY < 0 ? 1 : -1;

    setZoomLevel((value) => {
      const nextValue = direction > 0 ? Math.min(8, value * 1.2) : Math.max(1, value / 1.2);
      if (nextValue === 1) {
        setPanOffset({ x: 0, y: 0 });
      }
      return nextValue;
    });
  }

  return (
    <>
      <div className="map-toolbar">
        <div className="map-zoom-controls" aria-label="Map zoom controls">
          <button type="button" className="secondary-button map-tool-button" onClick={handleZoomOut}>
            -
          </button>
          <button type="button" className="secondary-button map-tool-button" onClick={handleZoomIn}>
            +
          </button>
          <button type="button" className="secondary-button map-tool-button" onClick={handleResetView}>
            Reset
          </button>
        </div>
        <p className="helper-text">Scroll to zoom and drag to pan.</p>
      </div>
      <svg
        ref={svgRef}
        className={`relocation-map ${isDragging ? "dragging" : ""}`}
        viewBox={viewBox}
        role="img"
        aria-label="NYC taxi zone map"
        onWheelCapture={handleWheel}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      >
        {pathItems.map((item) => (
          <path key={item.id} d={item.path} className={`zone-shape ${item.tone}`} data-zone-id={item.id}>
            <title>{`${item.zone} (${item.id})`}</title>
          </path>
        ))}
        {currentZoneCenter && (
          <g className="current-zone-star-layer">
            <circle
              cx={currentZoneCenter.x}
              cy={currentZoneCenter.y}
              r={Math.max(width, height) * 0.0135}
              className="current-zone-star-badge"
            />
            <path
              d={buildStarPath(currentZoneCenter.x, currentZoneCenter.y, Math.max(width, height) * 0.012)}
              className="current-zone-star-outline"
            />
            <path
              d={buildStarPath(currentZoneCenter.x, currentZoneCenter.y, Math.max(width, height) * 0.0105)}
              className="current-zone-star"
            >
              <title>Current zone marker</title>
            </path>
          </g>
        )}
      </svg>
    </>
  );
}

function buildStarPath(cx, cy, outerRadius) {
  const innerRadius = outerRadius * 0.45;
  const points = [];

  for (let index = 0; index < 10; index += 1) {
    const angle = (-Math.PI / 2) + (index * Math.PI) / 5;
    const radius = index % 2 === 0 ? outerRadius : innerRadius;
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    points.push(`${index === 0 ? "M" : "L"} ${x} ${y}`);
  }

  return `${points.join(" ")} Z`;
}

export default RelocationZoneMap;
