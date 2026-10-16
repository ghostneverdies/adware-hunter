"use strict";

const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
const storage = {
  get(key, session = false) { try { return (session ? sessionStorage : localStorage).getItem(key); } catch { return null; } },
  set(key, value, session = false) { try { (session ? sessionStorage : localStorage).setItem(key, value); } catch { } }
};
const fragment = new URLSearchParams(location.hash.slice(1));
const token = fragment.get("token") || storage.get("hunter-token", true) || "";
if (fragment.has("token")) {
  storage.set("hunter-token", token, true);
  history.replaceState(null, "", location.pathname);
}
let state = { demo: false, tools_ready: false, devices: [], serial: null, apps: [], reports: 0 };
let initialized = false;
let pending = false;
let currentPage = "connect";
let selectedPackage = null;
let removalTarget = null;
let guideIndex = 0;
let listSignature = "";
let pollFailures = 0;
const pageNames = { connect: "Connect", hunt: "Find the ad", review: "Review apps", finish: "Finish up" };
const pageOrder = Object.keys(pageNames);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
let motionEnabled = storage.get("hunter-motion") !== "off" && !reduceMotion.matches;

function applyMotion() {
  document.body.dataset.motion = motionEnabled && !reduceMotion.matches ? "on" : "off";
  $("#motion-toggle").setAttribute("aria-pressed", String(motionEnabled && !reduceMotion.matches));
}
applyMotion();
reduceMotion.addEventListener("change", applyMotion);
document.body.classList.toggle("large-text", storage.get("hunter-large-text") === "on");
$("#text-toggle").setAttribute("aria-pressed", String(document.body.classList.contains("large-text")));

function toast(message, error = false, persistent = false) {
  const element = document.createElement("div");
  element.className = "toast" + (error ? " error" : "");
  if (error) element.setAttribute("role", "alert");
  const text = document.createElement("p");
  text.textContent = message;
  const close = document.createElement("button");
  close.className = "icon-button";
  close.setAttribute("aria-label", "Dismiss message");
  close.textContent = "×";
  const dismiss = () => {
    element.classList.add("leaving");
    setTimeout(() => element.remove(), motionEnabled && !reduceMotion.matches ? 250 : 0);
  };
  close.addEventListener("click", dismiss);
  element.append(text, close);
  const region = $("#toast-region");
  if (region.children.length >= 3) region.firstElementChild.remove();
  region.append(element);
  if (!persistent) setTimeout(dismiss, error ? 12000 : 6500);
}

async function api(path, body) {
  const options = { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", credentials: "omit" };
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`/api/${path}`, options);
  const result = await response.json();
  if (!response.ok) {
    if (result.state) acceptState(result.state);
    throw new Error(result.error || "This action could not finish. Please try again.");
  }
  return result;
}

async function action(name, body = {}, message = "Working on it…", quiet = false) {
  if (pending || !initialized) return false;
  pending = true;
  if (!quiet) {
    $("#busy-message").textContent = message;
    $("#busy-bar").hidden = false;
    $("main").setAttribute("aria-busy", "true");
  }
  if (name === "capture") $(".capture-card").classList.add("recording");
  renderControls();
  try {
    const next = await api(name, body);
    acceptState(next);
    pollFailures = 0;
    return true;
  } catch (error) {
    if (!quiet) toast(error.message.includes("Failed to fetch") ? "The local app is not responding. Keep the Python app running, then refresh this page." : error.message, true, true);
    else {
      pollFailures++;
      $("#connection-label").textContent = "Connection needs attention";
      $("#connection-pill").classList.remove("connected");
      if (pollFailures === 2) toast("We couldn’t check your phone. Check the cable and keep the Python app running.", true, true);
    }
    return false;
  } finally {
    pending = false;
    $("#busy-bar").hidden = true;
    $("main").removeAttribute("aria-busy");
    $(".capture-card").classList.remove("recording");
    renderControls();
  }
}

function acceptState(next) {
  const previous = state;
  state = next;
  if (previous.serial !== next.serial) {
    selectedPackage = null;
    $("#capture-feedback").textContent = "There’s no hurry. We’re ready when you are.";
    $("#capture-feedback").classList.remove("success");
    if (!next.serial && ["hunt", "review"].includes(currentPage)) {
      go("connect", true, true);
      if (previous.serial) toast("Your phone is no longer ready. Reconnect it to continue.", true);
    }
  }
  render();
  if (previous.reports !== next.reports && motionEnabled && !reduceMotion.matches) {
    $("#report-count").classList.remove("pop-number");
    requestAnimationFrame(() => $("#report-count").classList.add("pop-number"));
  }
}

function renderControls() {
  const connected = initialized && Boolean(state.serial);
  for (const element of $$("button[data-go]")) {
    const page = element.dataset.go;
    element.disabled = pending || (["hunt", "review"].includes(page) && !connected);
  }
  $("#connect-next").disabled = pending || !connected;
  $("#review-next").disabled = pending || !connected || !state.reports;
  $("#capture-button").disabled = pending || !connected;
  $("#check-button").disabled = pending || !initialized || !state.tools_ready;
  $("#setup-button").disabled = pending || !initialized;
  $("#device-select").disabled = pending;
  const selected = state.apps.find(app => app.package === selectedPackage);
  $("#settings-button").disabled = pending || !connected || !selected;
  $("#remove-button").disabled = pending || !connected || !selected?.removable;
  for (const row of $$(".app-row")) row.disabled = pending;
}

function render() {
  const connected = Boolean(state.serial);
  const device = state.devices.find(item => item.serial === state.serial);
  const unauthorized = state.devices.some(item => item.state === "unauthorized");
  const offline = state.devices.some(item => item.state === "offline");
  $("#demo-banner").hidden = !state.demo;
  $("#connection-label").textContent = connected ? "Phone connected" : unauthorized ? "Permission needed" : state.devices.length > 1 ? "Choose a phone" : "Phone not connected";
  $("#connection-pill").classList.toggle("connected", connected);
  $("#connection-pill").classList.toggle("warning", unauthorized || offline);
  $(".device-card").classList.toggle("connected", connected);
  $("#device-title").textContent = connected ? device?.model || "Android phone connected" : unauthorized ? "One tap away" : "Ready when you are";
  $("#device-description").textContent = connected ? "Your phone is connected. You’re ready for the next step." : unauthorized ? "Unlock your phone and tap Allow in the USB debugging message." : "Your phone will appear here once it’s connected.";
  $("#connect-bar-title").textContent = connected ? "All connected. Let’s move on." : !state.tools_ready ? "One small setup before we start" : unauthorized ? "Check your phone’s screen" : state.devices.length > 1 ? "Which phone are we helping?" : offline ? "Let’s reconnect your phone" : "Let’s find your phone";
  $("#connect-bar-description").textContent = connected ? "Choose Continue whenever you’re ready." : !state.tools_ready ? "Download Google’s Android connection tools. Internet is needed for this step." : unauthorized ? "Tap Allow on your unlocked phone, then check again." : state.devices.length > 1 ? "Choose a ready phone from the list below." : offline ? "Unplug and reconnect the cable, then unlock your phone." : "Check the connection when you’re ready. Need help? Open the step-by-step guide.";
  $("#setup-button").hidden = state.tools_ready;
  $("#connect-next").hidden = !state.tools_ready;
  $("#check-button").hidden = !state.tools_ready;
  const picker = $("#device-select");
  const desired = state.serial || "";
  const signature = JSON.stringify(state.devices);
  if (picker.dataset.signature !== signature) {
    picker.dataset.signature = signature;
    picker.replaceChildren(new Option("Choose your phone…", ""));
    for (const item of state.devices) {
      const status = { device: "Ready", unauthorized: "Tap Allow on phone", offline: "Reconnect phone" }[item.state] || item.state;
      const option = new Option(`${item.model} · ${item.serial} · ${status}`, item.serial);
      option.disabled = item.state !== "device";
      picker.add(option);
    }
  }
  picker.value = desired;
  $("#device-select-wrap").hidden = state.devices.length < 2;
  $("#report-count").textContent = state.reports;
  $("#results-summary").textContent = `${state.reports} report${state.reports === 1 ? "" : "s"} · ${state.apps.length} app${state.apps.length === 1 ? "" : "s"} recorded`;
  renderApps();
  renderControls();
}

function makeIcon(id) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#i-${id}`);
  svg.append(use);
  svg.setAttribute("aria-hidden", "true");
  return svg;
}

function renderApps() {
  const signature = JSON.stringify(state.apps);
  if (signature !== listSignature) {
    listSignature = signature;
    const list = $("#app-list");
    list.replaceChildren();
    $("#empty-results").hidden = state.apps.length > 0;
    for (const app of state.apps) {
      const row = document.createElement("button");
      row.className = "app-row";
      row.dataset.package = app.package;
      row.setAttribute("aria-pressed", "false");
      const icon = document.createElement("span");
      icon.className = "app-monogram";
      icon.textContent = (app.name || "?").slice(0, 1).toUpperCase();
      icon.setAttribute("aria-hidden", "true");
      const text = document.createElement("span");
      text.className = "app-row-text";
      const title = document.createElement("strong");
      title.textContent = app.name || app.package;
      const note = document.createElement("small");
      note.textContent = `Visible during ${app.count} ad report${app.count === 1 ? "" : "s"}${app.removable ? "" : " · Protected"}`;
      text.append(title, note);
      row.append(icon, text, makeIcon("arrow"));
      row.addEventListener("click", () => {
        if (pending) return;
        selectedPackage = app.package;
        renderApps();
        renderControls();
      });
      list.append(row);
    }
  }
  const selected = state.apps.find(app => app.package === selectedPackage);
  if (!selected) selectedPackage = null;
  for (const row of $$(".app-row")) {
    const active = row.dataset.package === selectedPackage;
    row.classList.toggle("selected", active);
    row.setAttribute("aria-pressed", String(active));
    row.disabled = pending;
  }
  $("#detail-placeholder").hidden = Boolean(selected);
  $("#detail-content").hidden = !selected;
  if (selected) {
    $("#detail-app-icon").textContent = (selected.name || "?").slice(0, 1).toUpperCase();
    $("#detail-name").textContent = selected.name || "App name unavailable";
    $("#detail-package").textContent = selected.package;
    $("#detail-evidence").textContent = `Visible during ${selected.count} of your ad reports. This is a clue, not proof.`;
    $("#removal-note").textContent = selected.removable ? "You’ll be asked to confirm. Saved app data may be lost." : "This app is protected or outside the main profile. Removal is unavailable here.";
  }
}

function go(page, focus = true, force = false) {
  if (!(page in pageNames) || (pending && !force)) return;
  if (["hunt", "review"].includes(page) && !state.serial) page = "connect";
  currentPage = page;
  for (const section of $$(".page")) {
    const active = section.id === `page-${page}`;
    section.hidden = !active;
    section.classList.toggle("active", active);
  }
  for (const item of $$(".nav-item")) {
    const active = item.dataset.go === page;
    item.classList.toggle("active", active);
    item.classList.toggle("done", pageOrder.indexOf(item.dataset.go) < pageOrder.indexOf(page));
    if (active) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  }
  $("#breadcrumb").textContent = pageNames[page];
  document.title = `Adware Hunter · ${pageNames[page]}`;
  if (focus) {
    $(`#${page}-title`).focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: motionEnabled && !reduceMotion.matches ? "smooth" : "instant" });
  }
}

const guides = [
  ["A cable that does more than charge", "Connect your Android phone to this computer with a USB data cable. Unlock the phone and keep its screen on.\n\nIf it isn’t detected, try another cable or USB port. Some cables only charge."],
  ["Find the build number", "On your phone, open Settings and search for Build number. It’s often under About phone.\n\nOn Samsung phones, try About phone → Software information."],
  ["Unlock developer options", "Tap Build number seven times. Your phone may ask for its PIN.\n\nReturn to Settings and search for Developer options. You only need to unlock this menu once."],
  ["Turn on USB debugging", "Open Developer options and turn on USB debugging. This allows this computer to communicate with your phone.\n\nOnly approve a computer you trust. You don’t need root access."],
  ["Say hello to this computer", "Keep your phone unlocked. When Allow USB debugging? appears, tap Allow.\n\nNo message? Unplug and reconnect the cable. Some phones need a USB mode change; try File transfer if the connection is missing."],
  ["You’re ready to check", "Close this guide and choose Check connection.\n\nStill no connection? Windows may need your phone maker’s official USB driver. Linux may need device access rules (udev). You shouldn’t need to run the entire app as administrator or root."]
];

function renderGuide() {
  $("#help-step").textContent = `CONNECTION HELP · ${guideIndex + 1} OF ${guides.length}`;
  $("#help-title").textContent = guides[guideIndex][0];
  $("#help-body").textContent = guides[guideIndex][1];
  $("#help-back").disabled = guideIndex === 0;
  $("#help-next").replaceChildren(document.createTextNode(guideIndex === guides.length - 1 ? "Got it" : "Next step"), makeIcon("arrow"));
  $("#guide-progress").replaceChildren(...guides.map((_, index) => {
    const mark = document.createElement("span");
    mark.className = index <= guideIndex ? "active" : "";
    return mark;
  }));
}

function closeDialog(id) {
  const dialog = document.getElementById(id);
  if (!dialog.open) return;
  if (!motionEnabled || reduceMotion.matches) { dialog.close(); return; }
  dialog.classList.add("closing");
  setTimeout(() => { dialog.close(); dialog.classList.remove("closing"); }, 180);
}

for (const element of $$("[data-go]")) element.addEventListener("click", event => {
  event.preventDefault();
  go(element.dataset.go);
});
for (const element of $$("[data-help]")) element.addEventListener("click", () => {
  guideIndex = 0;
  renderGuide();
  $("#help-dialog").showModal();
});
for (const element of $$("[data-close]")) element.addEventListener("click", () => closeDialog(element.dataset.close));
$("#help-back").addEventListener("click", () => { if (guideIndex > 0) { guideIndex--; renderGuide(); } });
$("#help-next").addEventListener("click", () => {
  if (guideIndex === guides.length - 1) closeDialog("help-dialog");
  else { guideIndex++; renderGuide(); }
});
$("#keep-app").addEventListener("click", () => closeDialog("remove-dialog"));
$("#text-toggle").addEventListener("click", () => {
  const large = document.body.classList.toggle("large-text");
  $("#text-toggle").setAttribute("aria-pressed", String(large));
  storage.set("hunter-large-text", large ? "on" : "off");
});
$("#motion-toggle").addEventListener("click", () => {
  if (reduceMotion.matches) {
    toast("Your device’s reduced-motion setting is on, so animations stay off.");
    return;
  }
  motionEnabled = !motionEnabled;
  storage.set("hunter-motion", motionEnabled ? "on" : "off");
  applyMotion();
});
$("#setup-button").addEventListener("click", async () => {
  if (await action("setup", {}, "Downloading Google’s connection tools. This may take a moment…")) toast("Connection tools are ready. Connect your phone and follow the setup steps.");
});
$("#check-button").addEventListener("click", async () => {
  if (await action("check", {}, "Checking your phone’s connection…")) toast(state.serial ? "Your phone is connected. You’re ready to continue." : "No ready phone yet. Unlock your phone and follow the setup guide.");
});
$("#device-select").addEventListener("change", async event => {
  const serial = event.target.value;
  if (serial) await action("select", { serial }, "Selecting your phone…");
});
$("#capture-button").addEventListener("click", async () => {
  if (await action("capture", { serial: state.serial }, "Recording the app visible on your phone…")) {
    const feedback = $("#capture-feedback");
    feedback.textContent = `Recorded. ${state.reports} ad report${state.reports === 1 ? "" : "s"} for this phone.`;
    feedback.classList.remove("success");
    requestAnimationFrame(() => feedback.classList.add("success"));
    toast("Clue recorded. You can record another ad or review the apps.");
  }
});
$("#settings-button").addEventListener("click", async () => {
  if (await action("settings", { serial: state.serial, package: selectedPackage }, "Opening the app’s information on your phone…")) toast(state.demo ? "Preview: this opens the selected app’s information on a real connected phone." : "Look at your phone. The selected app’s information page is open.");
});
$("#remove-button").addEventListener("click", () => {
  const app = state.apps.find(item => item.package === selectedPackage);
  if (!app?.removable || pending) return;
  removalTarget = { serial: state.serial, package: app.package };
  $("#remove-app-name").textContent = `${app.name || "App name unavailable"}\n${app.package}`;
  $("#remove-title").textContent = state.demo ? "Preview removing this app?" : "Remove this app?";
  $("#remove-description").textContent = state.demo ? "This is a preview. No real phone will be changed. In a real session, removal affects the main phone profile and may delete the app’s saved data." : "This removes the app from the phone’s main profile and may delete its saved data. Reinstalling may not restore that data.";
  $("#remove-dialog").showModal();
  $("#keep-app").focus();
});
$("#confirm-remove").addEventListener("click", async () => {
  const target = removalTarget;
  if (!target) return;
  $("#remove-dialog").close();
  removalTarget = null;
  if (await action("remove", { ...target, confirmed: true }, "Removing the selected app. Keep your phone connected…")) {
    selectedPackage = null;
    renderApps();
    toast(state.demo ? "Preview complete. No real phone was changed." : "App removed. Use your phone for a while to check whether the unwanted ads return.");
  }
});
$("#remove-dialog").addEventListener("close", () => { removalTarget = null; });
$("#ads-stopped").addEventListener("click", () => {
  $("#finish-feedback").textContent = "Good to hear. Turn USB debugging off, then disconnect your phone when you’re ready.";
  $(".finish-emblem").animate([{ transform: "rotate(-6deg) scale(1)" }, { transform: "rotate(4deg) scale(1.12)" }, { transform: "rotate(-6deg) scale(1)" }], { duration: motionEnabled && !reduceMotion.matches ? 500 : 0, easing: "ease-out" });
});
$("#symptom").addEventListener("change", updateSymptom);
function updateSymptom() {
  const notes = [
    "Record the ad while it’s still visible. We’ll look for the app active at that moment.",
    "Ads inside a free app may be built in. Its ad-free option or removing the app may help.",
    "Touch and hold the unwanted notification on your phone to see which app sent it. Changing its notification settings may be enough.",
    "Check your browser’s site notification permissions and pop-up settings. A website can show unwanted ads without a separate adware app."
  ];
  $("#symptom-note").textContent = notes[$("#symptom").selectedIndex];
}
document.addEventListener("pointerdown", event => {
  const target = event.target.closest(".button, .nav-item, .app-row");
  if (!target || target.disabled || !motionEnabled || reduceMotion.matches) return;
  const rect = target.getBoundingClientRect();
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  ripple.setAttribute("aria-hidden", "true");
  ripple.style.left = `${event.clientX - rect.left}px`;
  ripple.style.top = `${event.clientY - rect.top}px`;
  target.append(ripple);
  setTimeout(() => ripple.remove(), 700);
});

async function boot() {
  updateSymptom();
  renderControls();
  if (!token) {
    $("#connection-label").textContent = "Open your session link";
    $("#connect-bar-title").textContent = "Open the link from the Python app";
    $("#connect-bar-description").textContent = "Start adware_hunter.py and open the full local link it prints. That link connects this page to your session.";
    toast("Open the full local link printed by Adware Hunter to connect to your session.", true, true);
    return;
  }
  try {
    const initial = await api("state");
    initialized = true;
    acceptState(initial);
    if (state.tools_ready) await action("check", {}, "Checking connection…", true);
    setInterval(() => {
      if (!pending && state.tools_ready && !document.hidden && !$$("dialog[open]").length) action("check", {}, "Checking connection…", true);
    }, 8000);
  } catch (error) {
    $("#connection-label").textContent = "Session unavailable";
    toast("Could not connect to your local session. Keep the Python app running and open its full local link again.\n\n" + error.message, true, true);
  }
}
boot();
