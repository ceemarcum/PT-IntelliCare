# Step 7: Frontend (React)

PT IntelliCare's UI is a **React** app (built with **Vite**) in the `frontend-react` folder. FastAPI serves the built version, so there's still only one server to start.

**Open it:** start the server as usual (`py -m uvicorn main:app --reload`) and go to http://127.0.0.1:8000/app

The built app (`frontend-react/dist`) is included, so you don't need Node.js just to run it. You only need Node.js to change the React code (see "Editing the React code" below).

## Screens

| Screen | File | Backend it calls |
|---|---|---|
| Sign in / create account | `src/pages/Login.jsx` | `/auth/register`, `/auth/login` |
| My plan (step-by-step overview) | `src/pages/Home.jsx` | injuries, check-ins, engine state, claims |
| 1. Injury input form (pain slider, symptoms, age, exercise habits) | `src/pages/Injury.jsx` | `POST /injury/submit` |
| 2. Daily check-in (pain and mobility sliders) + recovery log | `src/pages/Checkin.jsx` | `POST /pain/submit`, `GET /pain/history/{user_id}` |
| 3. Exercise recommendations | `src/pages/Exercises.jsx` | `POST /engine/recommend`, `/engine/state`, `/engine/notifications` |
| 4. Progress dashboard | `src/pages/Progress.jsx` | `/pain/history`, `/recovery-model/predict`, `/autoencoder/check` |
| 5. Insurance insights dashboard (the patient's own claims) | `src/pages/Insurance.jsx` | `/insurance/...` |

Shared code in `frontend-react/src`:

| File | What it does |
|---|---|
| `App.jsx` | Routes (React Router, hash links like `/app/#/checkin`) |
| `lib/AppContext.jsx` | Who's signed in, step progress for the nav check marks, toast messages |
| `lib/api.js` | Every API call |
| `lib/state.js` | Session and age/exercise answers saved in the browser |
| `lib/format.js` | Dates and pain/mobility words |
| `components/Layout.jsx` | Header and step navigation |
| `components/Slider.jsx` | The 0-10 pain and mobility sliders |
| `components/LineChart.jsx` | The pain and mobility chart (SVG, no chart library) |
| `components/GuidanceText.jsx` | Shows the RAG answer (lists, bold) safely |
| `components/ProfileFields.jsx` | Age and exercise questions |
| `components/ui.jsx` | Notices, badges, buttons, page headings |
| `styles.css` | All styling (colors are variables at the top) |

## How the user_id works

After sign-in the browser remembers the `user_id`, so no screen asks for it. Age and exercise habits are also remembered in the browser (the users table doesn't store them). If someone signs in on a new browser, the screens ask for them again.

## Editing the React code

Needs Node.js (https://nodejs.org, the LTS version). From the `frontend-react` folder:

1. Install the packages (once): `npm install`
2. Live development: start the FastAPI server, then run `npm run dev` and open http://localhost:5173/app/. Changes show up instantly, and API calls are passed to the server on port 8000.
3. When you're done, build it so FastAPI serves the new version: `npm run build` (updates `frontend-react/dist`).

## Backend changes

- `main.py`: serves `frontend-react/dist` at `/app`.
- `routes/auth_routes.py`: login also returns `full_name` (for the greeting).
- `routes/injury_routes.py`: `GET /injury/user/{user_id}` lists a user's injuries.

## Test it

1. Restart the server and open http://127.0.0.1:8000/app
2. **Create account**, then fill in the injury form: Knee, Stiffness, pain 7, age 30, "I exercise sometimes." Click **Save injury**.
3. **Daily check-in:** save 6 check-ins (pain / mobility): 7/4, 7/4, 6/5, 5/6, 4/7, 3/7. The log should say "Pain is going down".
4. **Exercises:** click **Update my plan**. Expected: "You moved up to intermediate" plus exercises.
5. **Progress:** the chart shows pain falling and mobility rising. Hover a point for its values.
6. **Insurance:** submit a claim, then add a check-in so the claim has data.
7. To see a 6-week history, sign in as `demo.slow@example.com` / `demo1234` (from `py -m insurance.demo_seed`). The app asks for age and exercise habits once on that browser: enter 30 and "I exercise sometimes."

The insurer endpoints (`GET /insurance/portfolio`, `GET /insurance/flagged`) stay in the backend but aren't shown in the app, since patients shouldn't see other people's claims. Use /docs to demo them.

The old plain-JavaScript version in the `frontend` folder is no longer used and can be deleted.
