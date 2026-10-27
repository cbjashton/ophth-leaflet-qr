/* Pilot data for the app's evaluation.

   Nothing is sent unless leaflets.json has a "statsCode" (a GoatCounter site code).
   With it switched on, each phone is asked once for the person's role and main clinic area,
   and the app sends anonymous counts to GoatCounter:

     install   first time the app is opened from the home screen
     open      app opened, or brought back after 15 minutes or more
     signup    role and area chosen, or changed
     code      a QR code shown (which leaflet; "-easy" for an Easy Read version)
     related   a code shown from "Also consider"
     view      a leaflet opened on the staff phone
     search    a search that found nothing (the words typed are never sent)
     fav       a leaflet added to favourites
     share     the app shared with a colleague
     feedback  the feedback form opened

   Each count carries: role, area (and site, if sites are set up), the local date and time,
   whether the phone was offline at the time, and a random phone number made on the phone
   (e.g. "p7k2m9qa") so the evaluation can count active phones and return use without knowing
   whose phone it is. GoatCounter adds browser, operating system, screen size and country.
   Never sent: names, email addresses, search words, anything about patients.

   Counts made with no signal are kept on the phone and sent later, with the time they happened.
   Each count is one GoatCounter "event": path  <event>/<role>/<area>[/<site>][/<leaflet>]
                                         title  <yyyy-mm-dd hh:mm ddd> | <phone> | online|offline
*/
(function () {
  const P = window.PILOT_STORE || "lqr-";              // localStorage prefix, set per app
  const get = (k, d) => { try { const v = localStorage.getItem(P + k); return v ? JSON.parse(v) : d } catch (e) { return d } };
  const put = (k, v) => { try { localStorage.setItem(P + k, JSON.stringify(v)) } catch (e) {} };
  const slug = s => String(s || "").toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "unknown";
  const pad = n => String(n).padStart(2, "0");
  const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  let cfg = {}, code = "", hiddenAt = 0, onSignup = null;

  function phone() {
    let id = get("phone", "");
    if (!id) { id = Array.from(crypto.getRandomValues(new Uint8Array(8)), b => "abcdefghjkmnpqrstuvwxyz23456789"[b % 31]).join("").slice(0, 8); put("phone", id) }
    return id;
  }
  const profile = () => get("profile", null);
  const on = () => !!code;
  function stamp() {
    const d = new Date();
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + " " + DAYS[d.getDay()];
  }

  function ev(name, leaflet) {
    if (!on()) return;
    const p = profile() || {};
    const parts = [name, slug(p.role), slug(p.area)];
    if ((cfg.sites || []).length) parts.push(slug(p.site));
    if (leaflet) parts.push(String(leaflet).replace(/[^\w-]/g, ""));
    const title = stamp() + " | " + phone() + " | " + (navigator.onLine === false ? "offline" : "online");
    const q = get("q", []); q.push([parts.join("/"), title]); put("q", q.slice(-1000));
    flush();
  }

  function flush() {
    if (!on() || navigator.onLine === false) return;
    const q = get("q", []); if (!q.length) return; put("q", []);
    q.forEach(([p, t], n) => setTimeout(() => {
      const img = new Image();
      img.src = "https://" + encodeURIComponent(code) + ".goatcounter.com/count?p=" + encodeURIComponent(p) + "&t=" + encodeURIComponent(t) +
        "&e=true&rnd=" + Math.random().toString(36).slice(2);
    }, n * 150));
  }

  function standalone() { try { return matchMedia("(display-mode: standalone)").matches || navigator.standalone === true } catch (e) { return false } }

  function opened() {
    if (!on()) return;
    if (standalone() && !get("installSent", false)) { put("installSent", true); ev("install") }
    ev("open");
  }

  /* ---------- the one-off "about you" sheet ---------- */
  function chips(box, list, chosen, name) {
    box.innerHTML = "";
    list.forEach(v => {
      const b = document.createElement("button"); b.type = "button"; b.className = "pchip"; b.textContent = v;
      b.setAttribute("aria-pressed", v === chosen); b.dataset.v = v;
      b.onclick = () => { box.querySelectorAll(".pchip").forEach(x => x.setAttribute("aria-pressed", x === b)); check() };
      box.append(b);
    });
    box.setAttribute("aria-label", name);
  }
  const picked = id => document.querySelector("#" + id + " .pchip[aria-pressed=true]")?.dataset.v || "";
  function check() {
    const ok = picked("pRole") && picked("pArea") && (!(cfg.sites || []).length || picked("pSite"));
    document.getElementById("pSave").disabled = !ok;
  }
  function openSheet() {
    const p = profile() || {};
    chips(document.getElementById("pRole"), cfg.roles || [], p.role, "Your role");
    chips(document.getElementById("pArea"), cfg.areas || [], p.area, "Where you mainly work");
    const hasSites = (cfg.sites || []).length;
    document.getElementById("pSiteWrap").hidden = !hasSites;
    if (hasSites) chips(document.getElementById("pSite"), cfg.sites, p.site, "Your site");
    const f = cfg.surveyForm; const a = document.getElementById("pSurvey"); a.hidden = !f; if (f) a.href = f;
    document.getElementById("pPhone").textContent = phone();
    document.getElementById("pClose").hidden = !profile();
    document.getElementById("pilotSheet").hidden = false;
    check();
  }
  function closeSheet() { document.getElementById("pilotSheet").hidden = true }

  function wire() {
    document.getElementById("pSave").onclick = () => {
      const was = profile();
      const p = { role: picked("pRole"), area: picked("pArea"), site: picked("pSite") || "", at: stamp() };
      put("profile", p); closeSheet();
      if (!was || was.role !== p.role || was.area !== p.area || was.site !== p.site) ev("signup");
      if (!was) opened();
      onSignup && onSignup();
    };
    document.getElementById("pClose").onclick = closeSheet;
    document.getElementById("pilotLink").onclick = e => { e.preventDefault(); openSheet() };
    addEventListener("online", flush);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") hiddenAt = Date.now();
      else if (hiddenAt && Date.now() - hiddenAt > 15 * 60 * 1000) { hiddenAt = 0; if (profile()) ev("open") }
    });
  }

  let wired = false;
  window.Pilot = {
    /* call with the leaflet list (statsCode and pilot settings) whenever it loads */
    start(shared, after) {
      const was = code;
      cfg = shared.pilot || {}; code = shared.statsCode || ""; onSignup = after || null;
      if (!wired) { wire(); wired = true }
      document.getElementById("pilotLink").hidden = !code;
      if (!code) return;
      if (!profile()) { openSheet(); return }
      if (!was) opened();
      flush();
    },
    ev,
    on,
    profile,
    /* for testing: what is waiting to send */
    queue: () => get("q", [])
  };
})();
