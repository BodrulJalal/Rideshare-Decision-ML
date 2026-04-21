function HeroSection() {
  return (
    <section className="hero">
      <div>
        <p className="eyebrow">Ride-Hailing Driver Toolkit</p>
        <h1>Pick better zones. Judge offers faster.</h1>
        <p className="hero-copy">
          A React frontend talks to a FastAPI backend to help drivers reposition toward stronger
          zones and quickly assess whether a ride offer is worth taking.
        </p>
      </div>
      <div className="hero-card">
        <p>Powered by two ML endpoints</p>
        <ul>
          <li>Relocation recommendations from the saved Uber zone ensemble</li>
          <li>Dropoff-zone prediction using pickup zone, ride type, time, and trip length</li>
          <li>Travel time and demand signals blended into the relocation ranking response</li>
        </ul>
      </div>
    </section>
  );
}

export default HeroSection;
