import RelocationZoneMap from "../../components/map/RelocationZoneMap";

function ZoneMapPanel({ currentZoneId, highlightedZoneIds, relocationGeoJson }) {
  return (
    <article className="panel map-panel">
      <h2>Zone Map</h2>
      {relocationGeoJson ? (
        <div className="map-card map-card-embedded">
          <RelocationZoneMap
            geoJson={relocationGeoJson}
            highlightedZoneIds={highlightedZoneIds}
            currentZoneId={currentZoneId}
          />
          <div className="map-legend">
            <span><i className="legend-swatch current" /> Current</span>
            <span><i className="legend-swatch recommended" /> Recommended</span>
            <span><i className="legend-swatch alternative" /> Top alternatives</span>
          </div>
        </div>
      ) : (
        <div className="result-card muted">
          <p>Loading taxi zone map...</p>
        </div>
      )}
    </article>
  );
}

export default ZoneMapPanel;
