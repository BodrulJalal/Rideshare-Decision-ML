function ToolSwitcherPanel({ activeTool, onToolChange }) {
  return (
    <section className="panel tool-switcher">
      <div className="section-header">
        <h2>Choose Tool</h2>
        <div className="segmented-control" aria-label="Model selector">
          <button
            type="button"
            className={activeTool === "relocation" ? "active" : ""}
            onClick={() => onToolChange("relocation")}
          >
            Relocator
          </button>
          <button
            type="button"
            className={activeTool === "trip" ? "active" : ""}
            onClick={() => onToolChange("trip")}
          >
            Trip Evaluator
          </button>
        </div>
      </div>
    </section>
  );
}

export default ToolSwitcherPanel;
