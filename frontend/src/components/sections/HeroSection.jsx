function HeroSection() {
  return (
    <section className="hero">
      <div>
        <p className="eyebrow">Rideshare Relocation Planner</p>
        <h1>Reposition toward better zones with clearer reasoning.</h1>
        <p className="hero-copy">
          A React frontend talks to a FastAPI backend to help drivers identify stronger waiting
          zones using historical trip patterns, estimated travel time, and NYC taxi-zone map data.
        </p>
      </div>
      <div className="hero-card">
        <p>How the relocator helps</p>
        <ul>
          <li>Recommends the best nearby zone to wait in based on expected earning opportunity</li>
          <li>Explains each recommendation with travel time, projected exposure gain, and top alternatives</li>
          <li>Shows the current zone, recommended zone, and contenders directly on the NYC taxi-zone map</li>
        </ul>
      </div>
    </section>
  );
}

export default HeroSection;
