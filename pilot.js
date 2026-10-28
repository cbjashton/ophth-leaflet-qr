/* Pilot data for the app's evaluation.

   Nothing is sent unless leaflets.json has a "statsCode" (a GoatCounter site code).
   With it switched on, each phone is asked once for the person's role and the clinic areas they work in
   (one or more),
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

   Each count carries: role, areas (and site, if sites are set up), the local date and time,
   whether the phone was offline at the time, and a random phone number made on the phone
   (e.g. "p7k2m9qa") so the evaluation can count active phones and return use without knowing
   whose phone it is. GoatCounter adds browser, operating system, screen size and country.
   Never sent: names, email addresses, search words, anything about patients.

   Counts made with no signal, or whose sending fails, are kept on the phone and sent later, with the time they happened.
   Each count is one GoatCounter "event": path  <event>/<role>/<areas>[/<site>][/<leaflet>]
                                         <areas> = every area chosen, joined with "+" in the order
                                         of "areas" in leaflets.json, e.g. accident-and-emergency+cornea-and-external-eye
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
  /* "round" in the pilot settings: change it to start afresh. Phones then forget the old sign-up,
     waiting counts and install flag, and everyone is asked again. */
  const round = () => String(cfg.round || "");
  function newRound() {
    if (get("round", "") === round()) return;
    ["profile", "q", "installSent"].forEach(k => { try { localStorage.removeItem(P + k) } catch (e) {} });
    put("round", round());
  }
  const profile = () => {
    const p = get("profile", null);
    if (p && !Array.isArray(p.areas)) p.areas = p.area ? [p.area] : [];   // profiles saved before areas were multi-select
    return p;
  };
  /* areas in the fixed order of the "areas" list, so the same choice always gives the same path */
  function areaOrder(list) {
    const known = cfg.areas || [];
    return [...new Set(list)].sort((a, b) => {
      const i = known.indexOf(a), j = known.indexOf(b);
      return (i < 0 ? 1e9 : i) - (j < 0 ? 1e9 : j) || a.localeCompare(b);
    });
  }
  const areaPath = list => areaOrder(list).map(slug).join("+") || "unknown";
  const on = () => !!code;
  function stamp() {
    const d = new Date();
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + " " + DAYS[d.getDay()];
  }

  function ev(name, leaflet) {
    if (!on()) return;
    const p = profile() || {};
    const parts = [name, slug(p.role), areaPath(p.areas || [])];
    if ((cfg.sites || []).length) parts.push(slug(p.site));
    if (leaflet) parts.push(String(leaflet).replace(/[^\w-]/g, ""));
    const title = stamp() + " | " + phone() + " | " + (navigator.onLine === false ? "offline" : "online");
    const q = get("q", []); q.push([parts.join("/"), title, uid()]); put("q", q.slice(-1000));
    flush();
  }
  const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

  /* Send waiting counts one at a time. Each stays on the phone until GoatCounter has received it,
     so a send that fails on weak signal is kept and tried again (when back online, at the next count,
     or when the app is next opened or brought back). */
  let sending = false;
  function send(p, t) {
    const url = "https://" + encodeURIComponent(code) + ".goatcounter.com/count?p=" + encodeURIComponent(p) + "&t=" + encodeURIComponent(t) +
      "&e=true&rnd=" + Math.random().toString(36).slice(2);
    return fetch(url, { mode: "no-cors", cache: "no-store", credentials: "omit", keepalive: true });
  }
  function flush() {
    if (!on() || sending || navigator.onLine === false) return;
    let q = get("q", []); if (!q.length) return;
    if (q.some(x => !x[2])) { q = q.map(x => x[2] ? x : [x[0], x[1], uid()]); put("q", q) }   // counts saved by an older version
    sending = true;
    let n = 0;
    const next = () => {                     // oldest first, including counts made while sending
      const first = get("q", [])[0];
      if (!first || ++n > 500 || !on() || navigator.onLine === false) { sending = false; return }
      const [p, t, id] = first;
      send(p, t).then(() => { put("q", get("q", []).filter(x => x[2] !== id)); setTimeout(next, 100) })
        .catch(() => { sending = false });   // not received: keep it and the rest for the next try
    };
    next();
  }

  function standalone() { try { return matchMedia("(display-mode: standalone)").matches || navigator.standalone === true } catch (e) { return false } }

  function opened() {
    if (!on()) return;
    if (standalone() && !get("installSent", false)) { put("installSent", true); ev("install") }
    ev("open");
  }

  /* ---------- the one-off "about you" sheet ---------- */
  /* chips: one choice, or several when multi is true (tap again to unpick) */
  function chips(box, list, chosen, name, multi) {
    const sel = [].concat(chosen || []);
    box.innerHTML = "";
    list.forEach(v => {
      const b = document.createElement("button"); b.type = "button"; b.className = "pchip"; b.textContent = v;
      b.setAttribute("aria-pressed", sel.includes(v)); b.dataset.v = v;
      b.onclick = () => {
        if (multi) b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") !== "true");
        else box.querySelectorAll(".pchip").forEach(x => x.setAttribute("aria-pressed", x === b));
        check();
      };
      box.append(b);
    });
    box.setAttribute("aria-label", name);
  }
  const pickedAll = id => Array.from(document.querySelectorAll("#" + id + " .pchip[aria-pressed=true]"), x => x.dataset.v);
  const picked = id => id === "pRole" ? (document.getElementById("pRoleSel").value || "") : pickedAll(id)[0] || "";
  /* roles: either ["Nurse", ...] or [{"group": "Nursing", "roles": ["Staff nurse", ...]}, ...] */
  const roleList = () => (cfg.roles || []).flatMap(r => typeof r === "string" ? [r] : r.roles || []);
  function roleSelect(chosen) {
    const sel = document.getElementById("pRoleSel");
    sel.innerHTML = '<option value="">Choose your role</option>';
    (cfg.roles || []).forEach(r => {
      const add = (parent, v) => { const o = document.createElement("option"); o.value = o.textContent = v; o.selected = v === chosen; parent.append(o) };
      if (typeof r === "string") add(sel, r);
      else { const g = document.createElement("optgroup"); g.label = r.group; (r.roles || []).forEach(v => add(g, v)); sel.append(g) }
    });
    sel.onchange = check;
  }
  function check() {
    const role = picked("pRole"), areas = pickedAll("pArea").length, site = !(cfg.sites || []).length || picked("pSite");
    const ok = role && areas && site;
    document.getElementById("pSave").disabled = !ok;
    const hint = document.getElementById("pNeed");
    if (hint) hint.textContent = ok ? "" : !role && !areas ? "Choose your role and at least one area to continue."
      : !role ? "Choose your role to continue." : !areas ? "Choose at least one area to continue." : "Choose your site to continue.";
  }
  function openSheet() {
    const p = profile() || {};
    roleSelect(p.role);
    chips(document.getElementById("pArea"), cfg.areas || [], p.areas, "Where you work: choose all that apply", true);
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
      const p = { role: picked("pRole"), areas: areaOrder(pickedAll("pArea")), site: picked("pSite") || "", at: stamp() };
      if (!p.role || !p.areas.length) return;                    // Save stays disabled until both are chosen
      put("profile", p); closeSheet();
      if (!was || was.role !== p.role || areaPath(was.areas) !== areaPath(p.areas) || was.site !== p.site) ev("signup");
      if (!was) opened();
      onSignup && onSignup();
    };
    document.getElementById("pClose").onclick = closeSheet;
    document.getElementById("pilotLink").onclick = e => { e.preventDefault(); openSheet() };
    addEventListener("online", flush);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") hiddenAt = Date.now();
      else if (hiddenAt && Date.now() - hiddenAt > 15 * 60 * 1000) { hiddenAt = 0; if (profile()) ev("open") }
      else flush();
    });
  }

  let wired = false;
  window.Pilot = {
    /* call with the leaflet list (statsCode and pilot settings) whenever it loads */
    start(shared, after) {
      const was = code;
      cfg = shared.pilot || {}; code = shared.statsCode || ""; onSignup = after || null;
      if (code) newRound();
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
