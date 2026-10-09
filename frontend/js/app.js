// Router: each screen lives at a #/hash and has its own file in js/screens/.
import { session } from "./state.js";
import { $, $$, esc, notice } from "./ui.js";

import * as auth from "./screens/auth.js";
import * as home from "./screens/home.js";
import * as injury from "./screens/injury.js";
import * as checkin from "./screens/checkin.js";
import * as exercises from "./screens/exercises.js";
import * as progress from "./screens/progress.js";
import * as insurance from "./screens/insurance.js";

const SCREENS = { login: auth, home, injury, checkin, exercises, progress, insurance };
const TITLES = { login: "Sign in", home: "My plan", injury: "Report injury", checkin: "Daily check-in",
                 exercises: "Exercises", progress: "Progress", insurance: "Insurance" };

let cleanup = null;

async function route() {
  let name = (location.hash.replace(/^#\/?/, "") || "home").split("?")[0];
  if (!SCREENS[name]) name = "home";
  if (!session.get() && name !== "login") { location.hash = "#/login"; return; }
  if (session.get() && name === "login") { location.hash = "#/home"; return; }

  const signedIn = Boolean(session.get());
  $("#sidenav").hidden = !signedIn;
  $("#topbar-user").hidden = !signedIn;
  if (signedIn) $("#user-name").textContent = session.get().full_name || session.get().email;
  for (const a of $$(".sidenav a")) {
    if (a.dataset.route === name) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  }
  document.title = `${TITLES[name]} · PT IntelliCare`;

  if (cleanup) { cleanup(); cleanup = null; }
  const main = $("#main");
  main.innerHTML = "";
  try {
    cleanup = (await SCREENS[name].render(main)) || null;
  } catch (err) {
    main.innerHTML = notice("bad", "Something went wrong", `<p>${esc(err.message)}</p>`);
  }
  main.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

$("#sign-out").addEventListener("click", () => {
  session.clear();
  location.hash = "#/login";
});
window.addEventListener("hashchange", route);
route();
