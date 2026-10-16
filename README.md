# Adware Hunter

[![GitHub stars](https://img.shields.io/github/stars/ghostneverdies/adware-hunter?style=flat-square&color=b5f58b)](https://github.com/ghostneverdies/adware-hunter/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ghostneverdies/adware-hunter?style=flat-square&color=7dd4ac)](https://github.com/ghostneverdies/adware-hunter/forks)
[![Open issues](https://img.shields.io/github/issues/ghostneverdies/adware-hunter?style=flat-square&color=e4c78b)](https://github.com/ghostneverdies/adware-hunter/issues)
[![Last commit](https://img.shields.io/github/last-commit/ghostneverdies/adware-hunter?style=flat-square&color=a7b5a9)](https://github.com/ghostneverdies/adware-hunter/commits)

![Python 3.10 or newer](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS](https://img.shields.io/badge/CSS-663399?style=flat-square&logo=css&logoColor=white)
![Computer platforms: Windows, macOS, Linux](https://img.shields.io/badge/Computer-Windows%20%7C%20macOS%20%7C%20Linux-304b38?style=flat-square)
![Target device: Android](https://img.shields.io/badge/Phone-Android-3DDC84?style=flat-square&logo=android&logoColor=white)

**A helping hand for unwanted ads on your Android phone.**

Adware Hunter runs on your computer and opens a simple interface in your web browser. Connect your Android phone with a USB cable, record an unwanted ad, and review the app that was visible when it appeared.

You do not need to know how to code. Follow the instructions for your computer below, one step at a time.

**Nothing is removed automatically. You choose what to do.**

- [What is adware?](#what-is-adware)
- [What you need](#what-you-need)
- [Set up on Windows](#set-up-on-windows)
- [Set up on macOS](#set-up-on-macos)
- [Connect your Android phone](#connect-your-android-phone)
- [Find and review an unwanted ad](#find-and-review-an-unwanted-ad)
- [Open the app again later](#open-the-app-again-later)
- [Need help?](#need-help)

## What is adware?

Adware is software that shows advertising, sometimes in unwanted or intrusive ways. On a phone, this might look like full-screen ads appearing when you are not using the app responsible, or ads interrupting other apps.

**An ad does not always mean your phone has adware.** A free game may include ordinary advertising. A website may have permission to send notifications. Browser pop-ups can also come from a website rather than another installed app.

Adware Hunter helps you investigate. It records which app is on screen when you report an ad. That is a useful clue, **not proof that the app caused it**. Apps that draw over other apps and notification ads may not be identified by this method.

This is an investigation tool, not a full antivirus scanner or a promise to stop every ad.

## What you need

- An **Android phone**. iPhones and iPads are not supported.
- A Windows, Mac, or Linux computer.
- A USB cable that transfers data. Some cables only charge.
- An internet connection for the first setup and downloads.
- A current web browser, such as Edge, Chrome, Firefox, or Safari.

The app uses Python 3.10 or newer. The instructions below install Python and Git, which downloads this project.

The browser interface uses Python's built-in tools: **no PyQt6, Node.js, or npm is needed**. The commands also install `colorama`, a small optional package that adds colors to the text-menu mode. No other third-party Python packages are needed.

Google's Android connection tools are downloaded by the app when you choose **Set up connection**. You do not need to install Android Studio.

## Before copying commands

Copy a command from a box, paste it into Terminal, and press **Enter** (called **Return** on a Mac). Wait for it to finish before continuing. You can paste several lines together when they are in the same box.

If a command reports an error, stop at that step and check [Need help?](#need-help). Scrolling text during installation is normal.

## Set up on Windows

### 1. Open Terminal

Click **Windows Search** on the taskbar, type **Terminal**, and open **Terminal** or **Windows Terminal**.

Use a **PowerShell** tab. If the tab says Command Prompt, click the small arrow beside the `+` button and choose **Windows PowerShell** or **PowerShell**.

You can paste with **Ctrl + V**. If Terminal asks whether to paste multiple lines, check that they match the box you copied, then choose **Paste anyway**.

### 2. Install Git and Python with WinGet

Copy and run:

```powershell
winget install --id Git.Git --exact --source winget --accept-source-agreements --accept-package-agreements
winget install --id Python.Python.3.13 --exact --source winget --scope user --accept-source-agreements --accept-package-agreements
```

Follow any installation prompts. These commands accept the installers' license agreements. If WinGet says a package is already installed and no update is available, you can continue.

**Close all Terminal windows, then open Terminal again from Windows Search.** This lets Windows find the newly installed programs.

Check that both programs are available:

```powershell
git --version
py -3.13 --version
```

Both commands should display a version number. If `winget` is not recognized, install or update **App Installer** from the Microsoft Store, reopen Terminal, and try again. See [Microsoft's WinGet instructions](https://learn.microsoft.com/en-us/windows/package-manager/winget/).

### 3. Download Adware Hunter

Copy and run:

```powershell
Set-Location $HOME
git clone https://github.com/ghostneverdies/adware-hunter.git adware-hunter
Set-Location adware-hunter
```

This creates an `adware-hunter` folder inside your Windows user folder. If Git says that folder already exists, use [Open the app again later](#open-the-app-again-later) if you previously downloaded this project there.

### 4. Install the Python package and start the app

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install colorama
.\.venv\Scripts\python.exe adware_hunter.py
```

The first command creates a small, separate Python environment for this project. **You do not need to activate it or change PowerShell's security settings.**

Your browser should open automatically. **Keep Terminal open while using the app.** Continue with [Connect your Android phone](#connect-your-android-phone).

## Set up on macOS

### 1. Open Terminal

Press **Command + Space**, type **Terminal**, and press **Return**.

You can paste with **Command + V**.

### 2. Install Homebrew

Homebrew installs programs from Terminal. If you already use Homebrew, skip this command.

Copy and run the installer from the [official Homebrew website](https://brew.sh/):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts. It may install Apple's command-line tools and ask for your Mac login password. **Nothing appears while you type the password—not even dots.** Type it and press **Return**.

After installation finishes, run this block. It finds Homebrew in its usual location on Apple Silicon or Intel Macs and makes it available in this Terminal window:

```bash
if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -x /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi
```

Also follow the installer's **Next steps** to make Homebrew available in future Terminal windows. For installation problems or older Macs, see the [official Homebrew installation guide](https://docs.brew.sh/Installation).

### 3. Install Git and Python with Homebrew

```bash
brew install git python
git --version
python3 --version
```

The last two commands should display version numbers. Wait for installation to finish before continuing.

### 4. Download Adware Hunter

Copy and run:

```bash
cd "$HOME"
git clone https://github.com/ghostneverdies/adware-hunter.git adware-hunter
cd adware-hunter
```

This creates an `adware-hunter` folder inside your Mac home folder. If that folder already contains this project, use [Open the app again later](#open-the-app-again-later).

### 5. Install the Python package and start the app

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install colorama
./.venv/bin/python adware_hunter.py
```

This keeps the project's Python package separate from macOS and Homebrew. You do not need `sudo` for these commands.

Your browser should open automatically. **Keep Terminal open while using the app.** Continue below.

## Linux

Install Git and Python 3.10+ using your distribution's package manager, including its Python venv support. Then use the macOS download and `.venv` commands above, skipping Homebrew. Android device access may require your distribution's udev rules. Run the app as your normal user.

## Connect your Android phone

The app has a **Show me the steps** guide. You can also follow these instructions:

1. **Prepare the computer.** If the app shows **Set up connection**, click it and wait for Google's connection tools to download.
2. **Plug in the phone.** Use a USB data cable. Unlock the phone and keep its screen on.
3. **Find Build number.** On the phone, open Settings and search for **Build number**. It is often under **About phone**. On Samsung phones, try **About phone → Software information**.
4. **Tap Build number seven times.** Enter your phone's PIN if asked. This reveals a settings menu called **Developer options**.
5. **Turn on USB debugging.** Return to Settings, search for **Developer options**, open it, and turn on **USB debugging**. This allows your computer to communicate with the phone.
6. **Approve the connection.** When **Allow USB debugging?** appears on your unlocked phone, tap **Allow**. Only approve a computer you trust.
7. **Check the connection.** In Adware Hunter, click **Check connection**. If several phones are connected, choose the one you want to use.
8. When the app says **Phone connected**, click **Continue**.

Menu names vary by phone. Some phones also need their USB mode changed to **File transfer** if they are not detected. This is a troubleshooting step, not a requirement on every phone.

## Find and review an unwanted ad

1. On **Find the ad**, choose where the unwanted ads appear. Read the suggestion shown beneath the selection.
2. Use your phone normally. When an unwanted ad appears, **leave it visible on the phone**.
3. On your computer, click **An ad appeared — record it**.
4. You can record more examples, then click **Review recorded apps**.
5. Select an app. Choose **Show app on phone** to inspect its information and recognize it before deciding.
6. If you choose **Remove this app…**, read the confirmation carefully. Select **Keep app** to cancel, or confirm removal.
7. Use your phone for a while to check whether the unwanted ads return. Choose **Finish for now** when you are done.

**Removal can delete an app's saved data. Reinstalling the app may not bring that data back.** Removal here is limited to user-installed apps in the phone's main profile. Protected apps cannot be removed through this interface.

An app's name is not always available. In that case, you will see its app identifier, such as `com.example.app`. Use **Show app on phone** to help identify it.

For notification ads, touching and holding the notification on your phone may reveal the sender. For website ads, check your browser's site notification and pop-up settings. Removing an app may not be necessary.

### Make the interface comfortable

- Choose **Larger text** in the side menu to make important text and controls bigger.
- Turn **Animations** off if you prefer a still interface. Your device's reduced-motion setting is respected automatically.
- Choose **Need a hand?** for the connection guide.
- On smaller screens, the side menu becomes a compact navigation bar. Use the icons and step labels to move between pages.

### When you are finished

On your phone, turn **USB debugging off** in Developer options. If you do not want the computer to remain trusted, choose **Revoke USB debugging authorizations**. This removes trust for all previously approved computers.

Unplug the phone. In Terminal, press **Ctrl + C** to stop Adware Hunter; then close the browser tab. Closing the tab alone does not stop the Python app.

## Open the app again later

You only need to do the installation once. Open Terminal and run the commands for your computer.

**Windows — PowerShell:**

```powershell
Set-Location "$HOME\adware-hunter"
.\.venv\Scripts\python.exe adware_hunter.py
```

**macOS or Linux:**

```bash
cd "$HOME/adware-hunter"
./.venv/bin/python adware_hunter.py
```

### Try the interface without connecting a phone

From the project folder, use preview mode. It uses example data and does not change a real phone.

**Windows:**

```powershell
.\.venv\Scripts\python.exe adware_hunter.py --demo
```

**macOS or Linux:**

```bash
./.venv/bin/python adware_hunter.py --demo
```

## Need help?

| What you see | What to try |
| --- | --- |
| `winget` is not recognized | Install or update **App Installer** from the Microsoft Store. Close and reopen Terminal. |
| `git` or `py` is not recognized on Windows | Finish the installations, close **all** Terminal windows, reopen Terminal, and try the version checks again. |
| `brew` is not found on a Mac | Run the Homebrew location block above and follow the installer's **Next steps**. |
| The download folder already exists | If it contains this project, use the reopening commands. You do not need to download another copy. |
| The browser did not open | Copy the **full local link** printed in Terminal, including everything after `#token=`, and paste it into your browser's address bar. |
| “Open your session link” or “Session unavailable” | Keep the Python app running and open its full printed link again. Each restart creates a new link. |
| The phone is not detected | Unlock it, check USB debugging, and try another data cable or USB port. If needed, try File transfer mode. |
| “Permission needed” | Look at the phone and tap **Allow** in its USB debugging message. Reconnect the cable if no message appears. |
| Windows still cannot find the phone | Your phone may need its manufacturer's official USB driver. |
| The app cannot tell which app is visible | Keep the ad visible and try again. Some overlays and notification ads cannot be identified this way. |
| “The interface files are missing” | Keep the entire `ui` folder beside `adware_hunter.py`. Do not move only the Python file. |
| An app cannot be removed | It may be protected, outside the main profile, or have device-admin restrictions. Inspect its information on the phone. |

If you ask for help in the repository's **Issues** section, include your computer's operating system, phone model, and the error message. Do not post your phone's PIN or the session link containing `#token=`.

## Privacy and limits

- The interface runs at an address starting with `http://127.0.0.1`. This means **this computer**, not a public website.
- Ad reports are held in memory for the current Python session. They are not uploaded by the app or saved as a permanent report. Stopping the app clears them.
- Initial setup downloads software, including Google's Android connection tools. Those downloads need internet access.
- Reports are kept separate for each selected phone.
- The tool does not root your phone, automatically remove apps, or guarantee that a recorded app is adware.
- This project does not investigate iPhones, iPads, or adware on the computer itself.

For installation references, see [Microsoft's WinGet install guide](https://learn.microsoft.com/en-us/windows/package-manager/winget/install), [Homebrew](https://brew.sh/), and [Homebrew's Python guidance](https://docs.brew.sh/Language-Runtimes-and-Packages).
