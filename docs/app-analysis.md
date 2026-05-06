# App Analysis

## Evaluation Goal

The goal of evaluation is to confirm that Driver Earnings Navigator is usable, technically functional, and clear enough for a driver to understand the relocation recommendation and supporting tradeoffs.

## Manual Test Plan

Manual testing was performed during local development with the backend and frontend running together.

| Test | Steps | Expected Result | Result |
|---|---|---|---|
| Backend health check | Start backend and visit `/api/health`. | API returns `status: ok`. | Pass. Backend ran successfully during app testing. |
| Load relocation zones | Open frontend with backend running. | Current-zone dropdown is populated. | Pass. Dropdown loaded zone names with location IDs for readability and accuracy. |
| Recommend from selected zone | Select a TLC zone and click recommend. | App displays recommended zone, travel time, adjusted earning exposure, and alternatives. | Pass. Results matched the model-building notebook output used to build the recommender. |
| Use current location | Click current-location button and allow browser location access. | App stores device location and can request a recommendation. | Pass with limitation. Browser geolocation worked, but sometimes reused a previous location before updating. |
| Map rendering | Open app after backend loads GeoJSON. | Taxi-zone map renders with legend. | Pass. NYC taxi-zone map loaded. Future improvement: add streets and landmarks for clearer human recognition. |
| Map highlighting | Request a recommendation. | Current, recommended, and alternative zones are highlighted. | Pass. Current, recommended, and alternative zones were clearly distinguishable. |
| Time override | Enable custom time and select a day/hour. | Recommendation uses selected day/hour. | Pass. Custom day/hour changed the recommendation context as expected. |
| Copilot chat | Ask for a relocation recommendation in natural language. | Copilot responds or shows a clear service error if API key is missing. | Pass with dependency. Copilot worked when the Gemini API key was valid and quota was available. |
| Error handling | Submit without enough location/zone information or trigger copilot failure. | App shows a clear error message. | Pass. Clear errors appeared for missing zone input and Gemini response failures. |

## Performance Metrics

Measured locally on the development machine. Backend measurements used `backend/.venv` and a temporary local Uvicorn port. Frontend measurements used a production Vite build and local Vite preview.

| Metric | Result | Notes |
|---|---:|---|
| Frontend build time | 2.68 seconds | `npm run build`; Vite reported the production build itself completed in 839 ms. |
| Backend startup time | 2.64 seconds | Time from starting Uvicorn to successful `/api/health` response using `backend/.venv`. |
| `/api/health` response time | 13.3 ms | Local request after backend was already running. |
| `/api/relocation-zones` response time | 859.9 ms | Returned TLC relocation zone options with location IDs and names. |
| `/api/relocation-zones-geojson` response time | 568.5 ms | Returned 263 taxi-zone GeoJSON features for the map. |
| `/api/recommend-zone` response time | 148.6 ms | Tested with Lower East Side, day 6, hour 2. |
| Frontend initial page load | 140.7 ms | Local production-preview proxy measurement for initial HTML plus built JS/CSS assets. |

## User Testing

### Participant 1

- Background: Friend, student, and part-time Uber driver.
- Task: Reviewed the app concept and the earlier offered-trip destination prediction idea.
- Result: The user understood the idea but said they would not reject rides based on a prediction.
- Feedback: Because they drive part-time, rejected rides could have a large effect on their driver rating and available perks. For that reason, predicting where an offered trip might go was not useful enough for the final product.
- Action taken or planned: Removed the offered-trip destination prediction feature from the final product focus and kept the app centered on relocation recommendations between trips.

### Participant 2

- Background: Neighbor, full-time Uber driver, around 40 years old.
- Task: Used or reviewed a relocation recommendation and explanation.
- Result: The user liked the explanation text and felt the recommended move made sense in context.
- Feedback: After using a recommendation to move zones, the user connected the result to real-world local activity, such as schools letting out and parents picking up children. This was positive feedback because the recommendation aligned with practical driver intuition.
- Action taken or planned: Kept explanation text as a key part of the app because it helped connect model output to real-world reasoning.

### Participant 3

- Background: General user feedback.
- Task: Reviewed the app flow and amount of reading required.
- Result: The user suggested adding a chatbot or voice option to reduce reading and make the app easier to interact with.
- Feedback: Some users may prefer asking questions naturally rather than reading all result fields manually.
- Action taken or planned: Added the Gemini-powered copilot with chat/voice interaction and emphasized key metrics in the interface.

## Error Tracking And Logging

Current implementation notes:

- The backend exposes a health endpoint for basic availability checks.
- Backend service failures are returned as HTTP errors instead of crashing the frontend.
- The frontend displays user-facing error messages for location, recommendation, and copilot failures.
- The model manager uses Python logging warnings when model artifacts or lookup files cannot be loaded.

TODO: Add final notes about any logs observed during testing.

## Findings And Iterations

| Finding | Evidence | Change Made Or Planned |
|---|---|---|
| Offered-trip prediction was not valuable enough for the final app. | Part-time Uber driver feedback said they would avoid rejecting trips because rejections could affect rating and perks. | Removed that feature from the final product focus. |
| Drivers need explanations, not just a recommended zone. | Full-time Uber driver feedback showed explanation text helped connect recommendations to real-world activity. | Kept travel time and adjusted earning exposure explanations as a core result feature. |
| Some users may prefer conversation over reading. | General feedback suggested adding a chatbot or voice option. | Added Gemini-powered copilot with voice/chat support. |
| Zone names alone are not always enough. | Testing showed the map helped differentiate current, recommended, and alternative zones. | Added color-coded map highlights and legend; future improvement is adding streets/landmarks. |
| Browser geolocation can be inconsistent. | Current-location testing sometimes reused a previous location before updating. | Kept manual zone selection as an alternative to device location. |

## Limitations

Current limitations to acknowledge honestly:

- The model is based on historical trip patterns and does not guarantee individual driver earnings but rather exposure to market earning potential for drivers to take part in.
- Recommendations depend on available training data for the selected zone, day, and hour.
- Device location support depends on browser permission and browser geolocation accuracy.
- Copilot functionality depends on a configured Gemini API key.
- Copilot functionality can also be limited by API quota or API availability.
- The current map uses taxi-zone outlines; future versions could add streets and landmarks for clearer zone recognition.
