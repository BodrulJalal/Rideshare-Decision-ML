# App Design

## Design Goal

Driver Earnings Navigator is designed around a short, high-pressure decision: an Uber driver has just finished a ride or is waiting without requests and needs to decide where to wait next. The interface prioritizes speed, map context, and explanation over dense analytics.

The app is especially focused on lower-demand periods. During rush hours, drivers may not need extra relocation support because ride requests are more frequent. During quieter parts of a shift, drivers have more time to safely pull over, check the app, and decide whether moving to a different zone is worth the travel time.

## Personas

### Persona 1: Full-Time NYC Uber Driver

- Age range: 19+
- Driving pattern: Full-time or high-volume driver, defined here as driving about 8 or more hours in a shift. A long shift can include both high-demand periods, such as morning rush, and slower periods afterward.
- Technical comfort: Comfortable using smartphone navigation and the Uber driver app. Full-time drivers are also more likely to recognize common zone and neighborhood names from experience.
- Pain points:
  - Gets used to rush-hour demand, then runs into slower parts of the day with fewer ride requests.
  - Wastes time waiting in zones with weak demand during quiet periods.
  - Needs to balance travel time against possible earning opportunity.
  - Wants to stay active and avoid boredom or demotivation during longer shifts.
  - Wants an explanation, not just a black-box recommendation, before deciding whether relocating is worth it.
- Needs:
  - Fast recommendation.
  - Clear current-zone and destination-zone context.
  - A short reason explaining the tradeoff between relocation time and adjusted earning exposure.
  - A tool that can be checked safely during downtime rather than while actively driving.

### Persona 2: Part-Time Or Newer NYC Uber Driver

- Age range: 19+
- Driving pattern: Drives part-time, possibly during off-peak hours, evenings, weekends, or around another schedule.
- Technical comfort: Comfortable with apps but may be unfamiliar with NYC TLC taxi-zone names or local demand patterns.
- Pain points:
  - Does not know which areas are worth relocating toward.
  - May not know their exact TLC zone or may use a different neighborhood name than the TLC zone name.
  - Needs guidance for what-if scenarios.
  - Has less intuition about which zones offer stronger ride opportunity.
- Needs:
  - Current-location option.
  - Map visualization.
  - Copilot/chat support for natural-language questions.

## User Journey

1. Driver opens the app before a shift, between rides, or during a slower period after safely pulling over.
2. Driver chooses a current TLC zone or uses device location.
3. Driver optionally overrides day and time for a what-if scenario or to plan whether a future start time may be worthwhile.
4. Driver clicks the recommendation button.
5. App displays the recommended zone, travel time, adjusted earning exposure, and top alternatives.
6. Driver checks the map to understand where the recommendation is relative to their current zone.
7. Driver can ask the copilot follow-up questions or test another scenario.
8. Driver uses the explanation and map context to decide whether relocating is worth it.

If the driver does not select a custom day or time, the app uses the device's current day and hour so the default workflow remains focused on the driver's current situation.

## Main Screens And Components

### Relocation Planner

The planner is the main decision surface. It asks for the driver's current zone or location and returns a concise recommendation.

Design rationale:

- The recommendation button keeps the main workflow simple.
- The zone dropdown supports drivers who know their TLC zone.
- The device-location option supports drivers who do not know their exact zone or use a different name for the area they are in.
- The results area emphasizes the recommended zone first, then supporting details that help the driver decide whether relocating is worth it.

### Time Settings Panel

The time settings panel lets users compare current conditions against another day and hour. It was also useful during development for debugging model behavior across different time inputs, but it remains valuable for drivers who want to plan a future shift or compare possible start times.

Design rationale:

- Many rideshare patterns are time-dependent.
- Optional controls avoid overwhelming users who just want a recommendation for right now.
- Preset time buttons make common scenarios faster to test.

### Zone Map

The map shows NYC TLC taxi zones and highlights the current, recommended, and alternative zones.

Design rationale:

- A text-only recommendation is not enough for every driver because TLC zone names may not clearly communicate where a zone is geographically.
- Drivers need spatial context before deciding to relocate.
- Color-coded highlights make it easier to compare options quickly.
- The legend explains color meaning so users do not rely on color alone.
- The current map shows NYC taxi-zone outlines. A future improvement would be adding streets or additional landmarks so zones are even easier to recognize.

### Top Alternatives

Top alternatives are included so the app does not present relocation as a single blind answer.

Design rationale:

- Drivers can compare nearby zones instead of assuming there is only one correct destination.
- If two zones have similar opportunity, the driver can choose based on their own route, traffic, or comfort with the area.
- Showing alternatives reduces the risk of every driver being directed to the same zone.

### Voice Copilot

The copilot supports typed or spoken questions about recommendations and what-if scenarios.

Design rationale:

- Natural-language input helps drivers ask questions without learning every control.
- Voice input is useful when a driver is thinking through a scenario.
- The copilot can explain recommendations in conversational language.
- Some users may be more comfortable asking an AI assistant a direct question than reading every result field manually.

## Accessibility Considerations

This project did not target a formal WCAG audit, but the current design includes several accessibility-oriented considerations:

- Form controls use visible labels.
- Buttons use visible text labels.
- The map includes an ARIA image label.
- The map legend pairs color with text labels.
- Responsive layout collapses to one column on smaller screens.
- Error messages are shown in the interface instead of failing silently.
- The app has been checked manually at different browser widths, and the main panels do not break when the window size changes.

TODO: Add final accessibility review notes if time allows.

- Keyboard navigation result: TODO
- Color contrast review result: TODO
- Screen reader check result: TODO

## Responsive Design

The layout uses a two-column desktop structure for the planner and map, then collapses to a single-column layout on smaller screens. This supports both laptop demos and mobile-like driver usage. During manual resizing, the app remained usable on both web and mobile-like widths, and the main panels did not break when the window size changed.

TODO: Add screenshots from desktop and mobile-width testing.

## Visual Style Guide

- Primary color: Green accent for recommendation/action states.
- Supporting color: Warm orange for current-location emphasis.
- Alternative-zone color: Blue highlight for top alternatives.
- Typography: Space Grotesk for headings and controls; Source Sans 3 for body text.
- Layout style: Panel-based dashboard with map and decision controls visible together.
- Tone: Practical, calm, and explanatory rather than gamified or overly technical.

## Design Iterations

| Iteration | Finding | Change |
|---|---|---|
| 1 | The project needed consistent data before app behavior could be trusted. | Started with data preparation using accessible, high-volume Uber ride data. |
| 2 | The core product needed to answer where a driver should wait next. | Built the recommendation logic and relocation model. |
| 3 | Raw recommendation output was not enough for decision-making. | Added explanation text around travel time and adjusted earning exposure. |
| 4 | Drivers should not blindly trust one answer. | Added top alternatives for comparison. |
| 5 | Zone names alone were not enough for geographic understanding. | Added a NYC taxi-zone map. |
| 6 | An offered-trip destination prediction feature was considered, but user feedback showed a driver may avoid rejecting trips because rejection can affect their own rating. | Removed that feature from the final product focus. |
| 7 | Drivers needed clearer visual comparison between zones. | Added colored highlights for current, recommended, and alternative zones with a legend. |
| 8 | Some users may prefer asking questions naturally. | Added the Gemini-powered copilot for dialogue, model context, and project-specific explanations. |
