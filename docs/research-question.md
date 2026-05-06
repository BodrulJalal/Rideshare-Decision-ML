# Research Question

## Question

How can a machine-learning-powered web app help NYC Uber drivers reduce unproductive waiting time by recommending nearby NYC TLC zones to relocate to using historical Uber trip patterns, estimated travel time, and adjusted earning exposure?

## Problem

NYC Uber drivers often decide where to wait between trips using experience, guesswork, or general knowledge of busy neighborhoods. This can lead to wasted time in weak-demand zones, especially during slower periods when the best waiting area may not be obvious.

The second part of the problem is that relocation is not automatically worth it. Drivers need to know whether the potential opportunity in another zone is strong enough to justify the travel time required to get there. Driver Earnings Navigator addresses this by recommending a better zone to wait in, explaining why that zone was selected, and showing the current, recommended, and alternative zones on a taxi-zone map.

## Target Users

- NYC Uber drivers who make frequent relocation decisions during each shift, who are most affected by decisions based on guesswork.
- Drivers who want quick, practical guidance between rides without reading raw data or interpreting model outputs.

Uber trip data specifically was selected because it was accessible through NYC Open Data, high-volume, and consistent enough to support the project goal without mixing multiple providers with different patterns or assumptions.

## Intended Impact

The app aims to help drivers:

- identify a recommended waiting zone in seconds,
- compare the recommended zone against top alternatives,
- understand the tradeoff between travel time and adjusted earning exposure,
- reduce guesswork when deciding whether to stay or reposition.

This is especially important during less busy times, when relocating may make a larger difference because demand is more uneven across zones. During very busy periods, relocation may be less necessary because more zones already have active demand.

## Success Criteria

- A driver can select a current zone or use device location and receive a recommendation.
- The app returns the recommended zone, estimated travel time, adjusted earning exposure, and top alternatives.
- The map visually distinguishes the current zone, recommended zone, and alternative zones.
- Each recommendation is explained using travel time and adjusted earning exposure so the driver can decide whether relocating is worth it.
- Users can understand the recommendation without needing to inspect raw model features or notebook outputs.
