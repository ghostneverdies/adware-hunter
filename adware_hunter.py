import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR = True
except ImportError:
    COLOR = False

    class _Dummy:
        def __getattr__(self, _):
            return ""

    Fore = _Dummy()
    Style = _Dummy()


def c(text, color):
    return f"{color}{text}{Style.RESET_ALL}" if COLOR else text


def banner():
    art = r"""
        _       _                          _   _             _
       / \   __| |_      ____ _ _ __ ___  | | | |_   _ _ __ | |_ ___ _ __
      / _ \ / _` \ \ /\ / / _` | '__/ _ \ | |_| | | | | '_ \| __/ _ \ '__|
     / ___ \ (_| |\ V  V / (_| | | |  __/ |  _  | |_| | | | | ||  __/ |
    /_/   \_\__,_| \_/\_/ \__,_|_|  \___| |_| |_|\__,_|_| |_|\__\___|_|

            A D W A R E   H U N T E R
"""
    print(c(art, Fore.CYAN))
    print(c("  Single purpose: find & remove the app that keeps showing you ads.\n", Fore.YELLOW))


def header(title):
    print()
    print(c("=" * 60, Fore.CYAN))
    print(c(f"  {title}", Fore.CYAN + Style.BRIGHT))
    print(c("=" * 60, Fore.CYAN))


def info(msg):
    print(c(f"[i] {msg}", Fore.BLUE))


def ok(msg):
    print(c(f"[+] {msg}", Fore.GREEN))


def warn(msg):
    print(c(f"[!] {msg}", Fore.YELLOW))


def err(msg):
    print(c(f"[x] {msg}", Fore.RED))


def pause():
    input(c("\nPress Enter to return to the menu...", Fore.MAGENTA))


def handle_unknown_error(exc, where=""):
    tb = traceback.format_exc()

    header("Unexpected Error")
    err("Something went wrong that this script wasn't expecting" + (f" (in: {where})" if where else "") + ".")
    print(c("""
  This isn't necessarily a bug in the script -- it can also be a device-
  specific quirk, a driver issue, or something about your particular
  phone/OS combo. Copy the block below EXACTLY as shown, and paste it
  into an AI assistant like ChatGPT (https://chatgpt.com), along with a
  sentence describing what you were doing when it happened (e.g. "this
  happened while connecting my phone"). Pasting the raw error text like
  this usually gives it enough to diagnose ADB/USB issues quickly.
""", Fore.YELLOW))
    print(c("  ---------------------------- COPY BELOW ----------------------------", Fore.WHITE))
    print(c(tb.strip(), Fore.WHITE))
    print(c("  ---------------------------- COPY ABOVE ----------------------------", Fore.WHITE))
    pause()


INSTALL_DIR = os.path.join(os.path.expanduser("~"), "android-sdk-platform-tools")

PLATFORM_TOOLS_URLS = {
    "Windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "Darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    "Linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
}

FOCUS_RE = re.compile(r"([a-zA-Z0-9_.]+)/[a-zA-Z0-9_.]+[}\s]")


def run(cmd, timeout=None):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise RuntimeError(f"Could not execute adb at '{cmd[0]}' -- the path may be broken or the file deleted.") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"adb command timed out after {timeout}s: {' '.join(cmd)}") from e


class State:
    def __init__(self):
        self.adb = None
        self.serial = None
        self.tally = {}


STATE = State()


def find_adb():
    on_path = shutil.which("adb")
    if on_path:
        return on_path
    local_adb = os.path.join(
        INSTALL_DIR, "platform-tools", "adb.exe" if platform.system() == "Windows" else "adb"
    )
    if os.path.isfile(local_adb):
        return local_adb
    return None


def install_platform_tools():
    system = platform.system()
    url = PLATFORM_TOOLS_URLS.get(system)
    if not url:
        err(f"Unsupported OS: {system}. Install Android SDK platform-tools manually.")
        return None

    info(f"adb not found. Downloading platform-tools for {system} ...")
    os.makedirs(INSTALL_DIR, exist_ok=True)
    zip_path = os.path.join(INSTALL_DIR, "platform-tools.zip")
    try:
        urllib.request.urlretrieve(url, zip_path)
        info("Download complete. Extracting ...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(INSTALL_DIR)
        os.remove(zip_path)
    except Exception as e:
        err(f"Download/extract failed: {e}")
        return None

    adb_path = os.path.join(
        INSTALL_DIR, "platform-tools", "adb.exe" if system == "Windows" else "adb"
    )
    if system != "Windows":
        os.chmod(adb_path, 0o755)

    if not os.path.isfile(adb_path):
        err("Installation failed: adb executable not found after extraction.")
        return None

    ok(f"platform-tools installed to: {os.path.join(INSTALL_DIR, 'platform-tools')}")
    info("Tip: add that folder to your PATH so 'adb' works from anywhere.")
    return adb_path


def ensure_adb():
    adb = find_adb()
    if adb:
        ok(f"Found adb at: {adb}")
        return adb
    return install_platform_tools()


def get_devices(adb):
    result = run([adb, "devices"])
    lines = result.stdout.strip().splitlines()[1:]
    devices = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))
    return devices


def explain_enable_usb_debugging():
    print(c("""
  How to enable USB debugging:

  Step 1 - Unlock Developer Options (hidden by default since Android 4.2):
    Settings > About phone > find "Build number" (on some phones:
    About phone > Software information) > tap it 7 times in a row.
    You'll see "You are now a developer!". The exact submenu name/location
    of "About phone" varies slightly by manufacturer skin (Samsung,
    Xiaomi/MIUI, OnePlus, etc.) but it's always inside Settings > About phone.

  Step 2 - Turn on USB debugging (the toggle's location depends on your
  Android version):
    - Android 9 and newer : Settings > System > Advanced > Developer options
                             > USB debugging
    - Android 8.0 / 8.1   : Settings > System > Developer options
                             > USB debugging
    - Android 7.1 and older: Settings > Developer options > USB debugging
    (Some manufacturers move "Developer options" to Settings > Additional
    settings, or put it as its own top-level entry -- if you don't see it
    under System, use the Settings search bar and type "developer".)

  Step 3 - Set the USB connection mode to File Transfer (this is required
  -- if the phone stays in "Charging" mode, it won't show up in adb at
  all, dialog or no dialog):
    1. Plug the phone into this computer with a USB cable.
    2. Pull down the phone's notification shade -- you'll see a
       notification like "Charging this device via USB" or
       "USB for charging".
    3. Tap that notification, then select "File Transfer" / "File
       Transfer / Android Auto" / "MTP" (wording varies by manufacturer).
       Do NOT leave it on "Charging only" / "No data transfer".

  Step 4 - Authorize the computer:
    1. Make sure the phone is UNLOCKED (screen on, not locked) -- the
       authorization dialog only appears on an unlocked screen.
    2. A dialog titled "Allow USB debugging?" showing an RSA key
       fingerprint should appear on the phone. Check "Always allow from
       this computer" and tap "Allow".

  If the device doesn't show up in adb at all, it's almost always the USB
  mode from Step 3 -- go back and check the notification shade.

  If it shows up but the dialog never appeared, it's usually one of these:
    - This exact computer was already authorized before (checked "Always
      allow" previously) -- in that case adb just connects with no
      prompt, which is normal, not a problem.
    - The phone's screen was locked when you plugged in -- unlock it,
      then unplug and replug the cable.
    - USB debugging was toggled on but the cable was never
      unplugged/replugged since -- unplug and replug it.
""", Fore.WHITE))


def diagnose_no_device():
    header("No Device Detected")
    info("(Type 'q' at any prompt to stop waiting and return to the menu.)")

    plugged = input(c("  Is your phone physically plugged into this computer with a USB cable right now? [y/n/q]: ", Fore.YELLOW)).strip().lower()
    if plugged == "q":
        return "cancel"
    if plugged != "y":
        info("Plug it in now, then continue.")
        input(c("  Press Enter once it's plugged in...", Fore.MAGENTA))
        return "retry"

    mode_ok = input(c("  Did you set the USB mode to 'File Transfer' from the notification shade (not 'Charging')? [y/n/q]: ", Fore.YELLOW)).strip().lower()
    if mode_ok == "q":
        return "cancel"
    if mode_ok != "y":
        warn("Pull down the notification shade, tap the USB notification, select 'File Transfer'.")
        input(c("  Press Enter once that's done...", Fore.MAGENTA))
        return "retry"

    debug_on = input(c("  Is USB debugging actually toggled ON in Settings > Developer options? [y/n/q]: ", Fore.YELLOW)).strip().lower()
    if debug_on == "q":
        return "cancel"
    if debug_on != "y":
        explain_enable_usb_debugging()
        input(c("  Press Enter once USB debugging is enabled...", Fore.MAGENTA))
        return "retry"

    warn("All three basics check out, so this may be a driver/OS-level issue:")
    print(c("""
    - Windows: the phone may need a USB driver (Google's USB driver, or
      your phone maker's OEM driver) before Windows will expose it to adb.
    - Linux: your user may need to be in the 'plugdev' group, or you may
      need a udev rule for this device -- try running with sudo as a test.
    - macOS: try a different USB cable/port -- some cables are charge-only.
    Also try: unplug the cable, wait 5 seconds, and plug it back in.
""", Fore.WHITE))
    choice = input(c("  Press Enter to check again, or 'q' to return to the menu: ", Fore.MAGENTA)).strip().lower()
    return "cancel" if choice == "q" else "retry"


def menu_setup_connect():
    header("Setup / Connect Device")

    if not STATE.adb:
        STATE.adb = ensure_adb()
        if not STATE.adb:
            err("Could not set up adb. Fix the issue above and try again.")
            pause()
            return

    has_debugging = input(c("Do you already have USB debugging enabled on your phone? [y/n]: ", Fore.WHITE)).strip().lower()
    if has_debugging != "y":
        explain_enable_usb_debugging()
        input(c("Press Enter once USB debugging is enabled and the phone is plugged in...", Fore.MAGENTA))
    else:
        info("Plug your phone in via USB now if it isn't already.")

    info("Checking connection ...")
    no_device_streak = 0
    while True:
        devices = get_devices(STATE.adb)

        if not devices:
            no_device_streak += 1
            if no_device_streak >= 6:
                result = diagnose_no_device()
                no_device_streak = 0
                if result == "cancel":
                    return
                continue
            time.sleep(1)
            continue

        no_device_streak = 0
        serial, dstate = devices[0]

        if dstate == "device":
            STATE.serial = serial
            ok(f"Device '{serial}' connected and authorized.")
            pause()
            return

        if dstate == "unauthorized":
            warn(f"Device '{serial}' is connected but NOT authorized.")
            print(c("""
   Fix:
    1. Unlock the phone's screen (the authorization dialog only shows
       on an unlocked screen -- this is the #1 reason it seems to
       "never appear").
    2. Check the notification shade -- USB mode should be "File
       Transfer", not "Charging".
    3. On the phone: Settings > Developer options >
       "Revoke USB debugging authorizations" -> confirm.
    4. Unplug and re-plug the USB cable.
    5. Watch the phone screen: a dialog titled "Allow USB debugging?"
       with an RSA key fingerprint should appear. Check "Always allow
       from this computer" and tap "Allow".
""", Fore.WHITE))
            resp = input(c("Press Enter after revoking + re-approving (or type 'q' + Enter to cancel): ", Fore.MAGENTA)).strip().lower()
            if resp == "q":
                return
            continue

        time.sleep(1)


def require_device():
    if not STATE.adb or not STATE.serial:
        warn("No connected/authorized device yet. Run 'Setup / Connect Device' first.")
        pause()
        return False

    devices = get_devices(STATE.adb)
    live = {s: st for s, st in devices}
    if live.get(STATE.serial) != "device":
        warn("Device no longer connected/authorized. Reconnect via 'Setup / Connect Device'.")
        pause()
        return False
    return True


def getprop(adb, prop):
    result = run([adb, "shell", "getprop", prop])
    return result.stdout.strip()


def menu_device_info():
    header("Device Info")
    if not require_device():
        return

    adb = STATE.adb
    model = getprop(adb, "ro.product.model") or "unknown"
    manufacturer = getprop(adb, "ro.product.manufacturer") or "unknown"
    android_ver = getprop(adb, "ro.build.version.release") or "unknown"
    sdk = getprop(adb, "ro.build.version.sdk") or "unknown"

    battery_raw = run([adb, "shell", "dumpsys", "battery"]).stdout
    level_match = re.search(r"level:\s*(\d+)", battery_raw)
    battery = f"{level_match.group(1)}%" if level_match else "unknown"

    print(c(f"  Manufacturer : {manufacturer}", Fore.WHITE))
    print(c(f"  Model        : {model}", Fore.WHITE))
    print(c(f"  Android      : {android_ver} (SDK {sdk})", Fore.WHITE))
    print(c(f"  Battery      : {battery}", Fore.WHITE))
    print(c(f"  Serial       : {STATE.serial}", Fore.WHITE))
    pause()


def menu_list_apps():
    header("Installed Apps (3rd-party)")
    if not require_device():
        return

    result = run([STATE.adb, "shell", "pm", "list", "packages", "-3"])
    packages = sorted(
        line.replace("package:", "").strip()
        for line in result.stdout.splitlines()
        if line.strip()
    )
    if not packages:
        warn("No user-installed apps found.")
    else:
        for i, pkg in enumerate(packages, 1):
            print(c(f"  {i:>3}. {pkg}", Fore.WHITE))
    pause()


def get_foreground_package(adb):
    result = run([adb, "shell", "dumpsys", "window"], timeout=15)
    text = result.stdout
    for key in ("mCurrentFocus", "mFocusedApp"):
        for line in text.splitlines():
            if key in line:
                match = FOCUS_RE.search(line)
                if match:
                    return match.group(1)
    return None


def menu_ad_hunt():
    header("Ad-Hunt Mode")
    if not require_device():
        return

    print(c("""
  Use your phone normally. The MOMENT an ad appears on screen
  (banner, full-screen, video) -- switch to this window and press Enter.
  The app in the foreground at that instant gets logged.

  Catch at least 5-10 ads for a reliable result. Type 'q' to finish.
""", Fore.WHITE))
    input(c("Press Enter to start monitoring...", Fore.MAGENTA))

    hits = 0
    while True:
        user_input = input(c(f"  [{hits} logged] Enter = log ad now, 'q' = finish: ", Fore.YELLOW))
        if user_input.strip().lower() == "q":
            break
        pkg = get_foreground_package(STATE.adb)
        if pkg:
            STATE.tally[pkg] = STATE.tally.get(pkg, 0) + 1
            hits += 1
            ok(f"logged foreground app: {pkg}")
        else:
            warn("couldn't determine foreground app, try again on the next ad")

    ok(f"Session finished: {hits} ad(s) logged.")
    pause()


def uninstall_package(adb, package_name):
    result = run([adb, "shell", "pm", "uninstall", "--user", "0", package_name])
    output = (result.stdout + result.stderr).strip()
    return "Success" in output, output


def menu_results():
    header("Results / Uninstall")
    while True:
        if not STATE.tally:
            warn("No ad-hunt data yet. Run 'Start Ad-Hunt Mode' first.")
            pause()
            return
        if not require_device():
            return

        ranked = sorted(STATE.tally.items(), key=lambda kv: kv[1], reverse=True)
        max_count = ranked[0][1]

        print(c("  Most frequently seen in foreground when an ad appeared:\n", Fore.WHITE))
        for i, (pkg, count) in enumerate(ranked, 1):
            bar = "#" * int((count / max_count) * 30)
            print(c(f"  {i:>2}. {pkg:<40} {bar} {count}", Fore.WHITE))

        print(c("""
  Note: if a legitimate free app (game, browser) tops this list, the ads
  may be built into that app rather than caused by separate adware.
""", Fore.WHITE))

        choice = input(c("  Enter number to uninstall, a package name, or 'q' to skip: ", Fore.YELLOW)).strip()
        if choice.lower() == "q":
            pause()
            return

        if choice.isdigit() and 1 <= int(choice) <= len(ranked):
            package_name = ranked[int(choice) - 1][0]
        else:
            package_name = choice

        confirm = input(c(f"  Confirm uninstall of '{package_name}'? [y/N]: ", Fore.RED)).strip().lower()
        if confirm != "y":
            info("Cancelled.")
            pause()
            return

        success, output = uninstall_package(STATE.adb, package_name)
        print(c(f"  {output}", Fore.WHITE))
        if success:
            ok(f"'{package_name}' uninstalled successfully.")
            STATE.tally.pop(package_name, None)
        else:
            err(f"Could not uninstall '{package_name}'.")
            warn("It may be a system app, or have device-admin privileges -- check")
            warn("Settings > Security > Device admin apps, deactivate it, then retry.")

        still_ads = input(c("\n  Still getting ads? Try again? [y/n]: ", Fore.YELLOW)).strip().lower()
        if still_ads != "y":
            pause()
            return

        info("Starting another ad-hunt round to gather fresh data ...")
        menu_ad_hunt()


def menu_revoke_help():
    header("Revoke USB Debugging Authorization")
    print(c("""
  ADB has no remote command to revoke authorizations -- it's a phone-side
  security control by design. To do it, open Developer options (path
  depends on Android version, see below) and tap
  "Revoke USB debugging authorizations":

    - Android 9 and newer : Settings > System > Advanced > Developer
                             options > Revoke USB debugging authorizations
    - Android 8.0 / 8.1   : Settings > System > Developer options >
                             Revoke USB debugging authorizations
    - Android 7.1 and older: Settings > Developer options >
                             Revoke USB debugging authorizations

  This forces every computer (including this one) to be re-approved next
  time it connects. Worth doing after removing an adware app, in case it
  tried to grant itself debugging trust.
""", Fore.WHITE))
    pause()


MENU_ITEMS = [
    ("1", "Setup / Connect Device", menu_setup_connect),
    ("2", "Device Info", menu_device_info),
    ("3", "List Installed Apps", menu_list_apps),
    ("4", "Start Ad-Hunt Mode", menu_ad_hunt),
    ("5", "View Results / Uninstall", menu_results),
    ("6", "Revoke USB Debug Auth (help)", menu_revoke_help),
    ("0", "Exit", None),
]


def status_line():
    dev = STATE.serial if STATE.serial else "not connected"
    hits = len(STATE.tally)
    return c(f"  Device: {dev}   |   Suspects logged: {hits}", Fore.MAGENTA)


def main_menu():
    while True:
        os.system("cls" if platform.system() == "Windows" else "clear")
        banner()
        print(status_line())
        header("Main Menu")
        for key, label, _ in MENU_ITEMS:
            print(c(f"  [{key}] {label}", Fore.WHITE))
        choice = input(c("\n  Select an option: ", Fore.CYAN)).strip()

        if choice == "0":
            print(c("\nGoodbye.\n", Fore.CYAN))
            sys.exit(0)

        match = next((m for m in MENU_ITEMS if m[0] == choice), None)
        if match:
            try:
                match[2]()
            except Exception as e:
                handle_unknown_error(e, where=match[1])
        else:
            warn("Invalid choice.")
            time.sleep(1)

class DeviceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    model: str


@dataclass(frozen=True)
class Observation:
    package: str
    name: str
    removable: bool


PACKAGE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+\Z")
HUNT_FOCUS_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_.]*)/[A-Za-z0-9_.$]+")
TOOLS_DIR = Path.home() / "android-sdk-platform-tools"
URLS = {
    "Windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "Darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    "Linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
}


def parse_devices(output: str) -> list[Device]:
    devices = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2 or line.startswith(("List ", "*")):
            continue
        model = next((p[6:].replace("_", " ") for p in parts[2:] if p.startswith("model:")), "Android phone")
        devices.append(Device(parts[0], parts[1], model))
    return devices


def parse_foreground(output: str) -> str | None:
    for key in ("mCurrentFocus", "mFocusedApp", "topResumedActivity", "mResumedActivity"):
        for line in output.splitlines():
            if key in line:
                match = HUNT_FOCUS_RE.search(line)
                if match:
                    return match.group(1)
    return None


class AdbBackend:
    def __init__(self):
        executable = "adb.exe" if platform.system() == "Windows" else "adb"
        local = TOOLS_DIR / "platform-tools" / executable
        self.adb = shutil.which("adb") or (str(local) if local.is_file() else None)

    def install_tools(self):
        url = URLS.get(platform.system())
        if not url:
            raise DeviceError("This computer's operating system is not supported.")


        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(dir=TOOLS_DIR) as temporary:
                root = Path(temporary)
                archive = root / "tools.zip"
                with urllib.request.urlopen(url, timeout=30) as response, archive.open("wb") as target:
                    shutil.copyfileobj(response, target)
                with zipfile.ZipFile(archive) as bundle:
                    for item in bundle.infolist():
                        path = (root / item.filename).resolve()
                        if not path.is_relative_to(root.resolve()):
                            raise DeviceError("The connection tools download contains an invalid file path.")
                    bundle.extractall(root)
                source = root / "platform-tools"
                executable = source / ("adb.exe" if platform.system() == "Windows" else "adb")
                if not executable.is_file():
                    raise DeviceError("The download did not contain the connection tools. Please try again.")
                shutil.copytree(source, TOOLS_DIR / "platform-tools", dirs_exist_ok=True)
            target = TOOLS_DIR / "platform-tools" / executable.name
            if platform.system() != "Windows":
                target.chmod(0o755)
            self.adb = str(target)
        except DeviceError:
            raise
        except Exception as exc:
            raise DeviceError("Could not download the connection tools. Check your internet connection and try again.") from exc
        return self.devices()

    def command(self, *args: str, serial: str | None = None, timeout: int = 20) -> str:
        if not self.adb:
            raise DeviceError("Set up the connection tools first.")
        command = [self.adb]
        if serial:
            command += ["-s", serial]
        command.extend(args)
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except subprocess.TimeoutExpired as exc:
            raise DeviceError("Your phone took too long to respond. Unlock it, check the cable, and try again.") from exc
        except OSError as exc:
            raise DeviceError("The connection tools could not start. Check their installation and try again.") from exc
        if result.returncode:
            raise DeviceError("The phone could not complete this action. Check its connection and authorization.\n\n" + result.stderr.strip())
        return result.stdout.strip()

    def devices(self) -> list[Device]:
        return parse_devices(self.command("devices", "-l"))

    def ready(self, serial: str):
        if not any(d.serial == serial and d.state == "device" for d in self.devices()):
            raise DeviceError("Your phone is disconnected or needs permission. Reconnect it and tap Allow on the phone.")

    def observe(self, serial: str) -> Observation:
        self.ready(serial)
        output = self.command("shell", "dumpsys", "window", serial=serial)
        package = parse_foreground(output)
        if not package:
            package = parse_foreground(self.command("shell", "dumpsys", "activity", "activities", serial=serial))
        if not package:
            raise DeviceError("We could not identify the app on screen. Keep the ad visible and try again.")
        user_apps = self.user_apps(serial)
        details = self.command("shell", "dumpsys", "package", package, serial=serial)


        label = re.search(r"nonLocalizedLabel=([^\r\n}]+)", details)
        name = label.group(1).strip() if label else ""
        if name in ("null", "None"):
            name = ""
        return Observation(package, name, package in user_apps)

    def user_apps(self, serial: str) -> set[str]:
        output = self.command("shell", "pm", "list", "packages", "-3", "--user", "0", serial=serial)
        return {line.removeprefix("package:").strip() for line in output.splitlines() if line.startswith("package:")}

    def app_settings(self, serial: str, package: str):
        self.validate_package(package)
        self.ready(serial)
        self.command("shell", "am", "start", "-a", "android.settings.APPLICATION_DETAILS_SETTINGS", "-d", "package:" + package, serial=serial)

    def remove(self, serial: str, package: str):
        self.validate_package(package)
        self.ready(serial)
        if package not in self.user_apps(serial):
            raise DeviceError("This app is protected or is not installed in the phone's main profile. It cannot be removed here.")
        output = self.command("shell", "pm", "uninstall", "--user", "0", package, serial=serial, timeout=45)
        if output.strip() != "Success":
            raise DeviceError("The phone did not remove this app. Open its settings on the phone for more information.\n\n" + output)
        return package

    @staticmethod
    def validate_package(package: str):
        if not PACKAGE_RE.fullmatch(package):
            raise DeviceError("This app identifier is invalid. Please record the ad again.")


class DemoBackend:

    adb = "demo"

    def __init__(self):
        self.removed = set()

    def devices(self):
        return [Device("preview-phone", "device", "Example Android phone")]

    def observe(self, serial):
        if "com.example.flashlight" in self.removed:
            return Observation("com.example.game", "Example game", True)
        return Observation("com.example.flashlight", "Example flashlight", True)

    def app_settings(self, serial, package):
        return None

    def remove(self, serial, package):
        self.removed.add(package)
        return package


import argparse
import json
import secrets
import threading
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class LocalApp:
    def __init__(self, demo=False, backend=None):
        self.demo = demo
        self.backend = backend or (DemoBackend() if demo else AdbBackend())
        self.token = secrets.token_urlsafe(32)
        self.devices = []
        self.serial = None
        self.sessions = {}
        self.operation = threading.Lock()
        self.lock = threading.RLock()

    def snapshot(self):
        with self.lock:
            records = self.sessions.get(self.serial, {})
            apps = [dict(asdict(observation), count=count) for observation, count in records.values()]
            return {
                "demo": self.demo,
                "tools_ready": bool(self.backend.adb),
                "serial": self.serial,
                "devices": [asdict(device) for device in self.devices],
                "apps": sorted(apps, key=lambda app: app["count"], reverse=True),
                "reports": sum(app["count"] for app in apps),
                "busy": self.operation.locked(),
            }

    def refresh(self, devices):
        with self.lock:
            self.devices = devices
            ready = [d.serial for d in devices if d.state == "device"]
            if self.serial not in ready:
                self.serial = ready[0] if len(devices) == 1 and len(ready) == 1 else None

    def action(self, name, body):
        if not self.operation.acquire(blocking=False):
            raise DeviceError("An action is already running. Please let it finish first.")
        try:
            if name == "check":
                self.refresh(self.backend.devices())
            elif name == "setup":
                self.refresh(self.backend.install_tools())
            elif name == "select":
                serial = body.get("serial")
                devices = self.backend.devices()
                self.refresh(devices)
                if not any(d.serial == serial and d.state == "device" for d in devices):
                    raise DeviceError("That phone is not ready. Unlock it and approve the connection first.")
                with self.lock:
                    self.serial = serial
            elif name in ("capture", "settings", "remove"):
                with self.lock:
                    serial = self.serial
                if not serial or body.get("serial") != serial:
                    raise DeviceError("The selected phone changed. Check the connection and try again.")
                if name == "capture":
                    observation = self.backend.observe(serial)
                    with self.lock:
                        session = self.sessions.setdefault(serial, {})
                        prior = session.get(observation.package)
                        session[observation.package] = (observation, prior[1] + 1 if prior else 1)
                else:
                    package = body.get("package")
                    with self.lock:
                        recorded = self.sessions.get(serial, {}).get(package)
                    if not recorded:
                        raise DeviceError("This app is not in this phone's recorded results.")
                    if name == "settings":
                        self.backend.app_settings(serial, package)
                    else:
                        if body.get("confirmed") is not True:
                            raise DeviceError("Confirm removal before continuing.")
                        if not recorded[0].removable:
                            raise DeviceError("This app is protected and cannot be removed here.")
                        self.backend.remove(serial, package)
                        with self.lock:
                            self.sessions[serial].pop(package, None)
            else:
                raise DeviceError("This action is not available.")
        finally:
            self.operation.release()
        return self.snapshot()


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, app):
        self.app = app
        self.ui_root = Path(__file__).resolve().parent / "ui"
        super().__init__(address, LocalHandler)


class LocalHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def trusted_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def authorized(self):
        supplied = self.headers.get("Authorization", "")
        return secrets.compare_digest(supplied, "Bearer " + self.server.app.token)

    def do_GET(self):
        if not self.trusted_host():
            self.respond(403, {"error": "This interface is available only on this computer."})
            return
        path = urlsplit(self.path).path
        if path == "/api/state":
            if not self.authorized():
                self.respond(403, {"error": "Open the full local link printed by Adware Hunter."})
                return
            self.respond(200, self.server.app.snapshot())
            return
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/favicon.svg": ("favicon.svg", "image/svg+xml"),
        }
        if path not in assets:
            self.respond(404, {"error": "Page not found."})
            return
        filename, content_type = assets[path]
        try:
            self.respond(200, (self.server.ui_root / filename).read_bytes(), content_type)
        except OSError:
            self.respond(404, {"error": "The interface files are missing. Keep the ui folder beside adware_hunter.py."})

    def do_POST(self):
        origin = self.headers.get("Origin")
        expected_origin = "http://" + self.headers.get("Host", "")
        if not self.trusted_host() or not self.authorized() or (origin and origin != expected_origin):
            self.respond(403, {"error": "This request is not authorized for this local session."})
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self.respond(415, {"error": "A JSON request is required."})
            return
        path = urlsplit(self.path).path
        if path not in ("/api/check", "/api/setup", "/api/select", "/api/capture", "/api/settings", "/api/remove"):
            self.respond(404, {"error": "Action not found."})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 0 or size > 65536:
                self.respond(413, {"error": "This request is too large."})
                return
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object")
            if any(key in body and not isinstance(body[key], str) for key in ("serial", "package")):
                raise ValueError("Invalid phone or app identifier")
            self.respond(200, self.server.app.action(path.rsplit("/", 1)[1], body))
        except (ValueError, TypeError):
            self.respond(400, {"error": "The request was not understood. Refresh the page and try again."})
        except DeviceError as exc:
            self.respond(409, {"error": str(exc), "state": self.server.app.snapshot()})
        except Exception:
            self.respond(500, {"error": "This action could not finish. Check the phone connection and try again."})


def launch_web():
    parser = argparse.ArgumentParser(description="Adware Hunter — a local Android ad investigation tool")
    parser.add_argument("--demo", action="store_true", help="Use example data without changing any phone")
    parser.add_argument("--no-browser", action="store_true", help="Print the local link without opening it")
    parser.add_argument("--port", type=int, default=0, help="Local port; default chooses an available port")
    parser.add_argument("--cli", action="store_true", help="Use the original text menu")
    options = parser.parse_args()
    if not 0 <= options.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    if options.cli:
        main_menu()
        return
    app = LocalApp(demo=options.demo)
    try:
        server = LocalServer(("127.0.0.1", options.port), app)
    except OSError as exc:
        raise SystemExit(f"Could not start the local interface: {exc}. Try a different --port.") from exc
    if not (server.ui_root / "index.html").is_file():
        server.server_close()
        raise SystemExit("Keep the ui folder beside adware_hunter.py, then start again.")
    url = f"http://127.0.0.1:{server.server_port}/#token={app.token}"
    print("\nAdware Hunter" + (" — PREVIEW MODE" if options.demo else ""), flush=True)
    print("Open this local link in your browser:\n" + url, flush=True)
    print("Keep this process running. Press Ctrl+C to stop.\n", flush=True)
    if not options.no_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        print("\nAdware Hunter stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    launch_web()

