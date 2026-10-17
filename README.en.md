<p align="center">
  <img src="docs/assets/mystery-cover-art.png" alt="Mystery nebula cover" width="100%">
</p>

<h1 align="center">Mystery</h1>

<p align="center">Read charts, draw cards, and remember your friends' birthdays.</p>
<p align="center">Charts · Divination · People · Music</p>

<p align="center">
  <a href="CHANGELOG.md"><img src="docs/assets/badges/version.svg" alt="Version 0.11.1"></a>
  <a href="LICENSE"><img src="docs/assets/badges/license.svg" alt="License: AGPL-3.0-only"></a>
  <a href="#windows"><img src="docs/assets/badges/windows.svg" alt="Windows 10 / 11"></a>
  <a href="#macos"><img src="docs/assets/badges/macos.svg" alt="macOS arm64 test build"></a>
  <a href="#privacy"><img src="docs/assets/badges/privacy.svg" alt="Data: stored locally"></a>
  <a href="#ai"><img src="docs/assets/badges/ai.svg" alt="AI: bring your own key"></a>
</p>

<p align="center"><a href="README.md">中文</a> · <a href="#why-i-made-it">Why I made it</a> · <a href="#four-parts">Features</a> · <a href="#run-it">Run it</a></p>

**Your records stay on your computer.** Birthdays, notes about friends and saved readings are stored locally, with no cloud sync. Relevant content is sent to your configured LLM provider only when you request an AI interpretation or follow-up. See [privacy details](#privacy).

## Why I made it

I've been interested in astrology and divination for a while, and I like trying them with friends. Mystery started as a tool I wanted to use myself and share with them.

With AI, I thought I could try giving it the cards or a chart and talking through the question that brought me there. Bring your own API key from a compatible provider, enter it in Settings, and you can ask for interpretations and follow up. Charts, card draws and the other local features also work without AI.

Sometimes I'm curious about how different traditions describe the same person. Sometimes something is bothering me and I just want a way to start talking about it. That's what I hope this app can do for my friends and me. I take the readings as something to think about; I still make my own decisions.

Along the way, I added birthdays, a map and a music player. The app now has four parts. The interface is currently in Chinese.

## Four parts

The app opens on a nebula. You can move around the scene or use the top navigation to open a feature. Motion and graphics quality are adjustable in Settings.

![Mystery home](docs/assets/mystery-home-silver.jpg)

### Charts

I wanted to see what different systems would say about the same birth information. Mystery includes Four Pillars, Western astrology, Zi Wei Dou Shu and Jyotish. You can compare them or ask AI about a particular part of a reading.

Select planets, palaces or pillars for details. Calculation rules and raw results are available too.

![Western natal chart](docs/assets/mystery-natal-silver.jpg)

### Divination

For questions you haven't made up your mind about, from something that's been worrying you to what to eat tonight.

There are Tarot, Lenormand, Liu Yao, Plum Blossom and the Book of Answers. You can shuffle, cut and draw cards, or toss coins one round at a time. I wanted to keep the hands-on part; it's fun to do with friends. Read the result yourself, or ask AI to interpret it and talk about why you asked.

![Tarot table](docs/assets/mystery-tarot-silver.jpg)

### People

This part is for keeping track of family and friends. When people live in different cities, it's nice to open a globe and see where everyone is.

Save birthplaces, current cities and birthdays, choose a color for each person, and add notes. They might be things you want to tell them or something to bring up next time you meet. While the app is open, birthday reminders use each friend's local time zone.

These records stay on your computer. The map and city search work offline.

![Friends on the birthday globe](docs/assets/mystery-atlas-silver.jpg)

### Music

Sometimes I don't want a reading. I just want to put on some music and get on with something.

Choose a local music folder and let the nebula or globe turn in the background. Direct audio links and a focus mode are also available.

<sub>The screenshots use fictional people, birthdays and questions. The cover is an AI-generated illustration.</sub>

## Run it

<a id="windows"></a>

**Windows:** use `Mystery-0.11.1-setup.exe`. The installer bundles Python, Node.js and offline assets. It requires Windows 10/11 x64, [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) and a WebGL 2 capable graphics driver. See [the desktop guide](DESKTOP.md).

<a id="macos"></a>

**macOS:** an Apple Silicon (arm64) test installer, `Mystery-0.11.1-macos-arm64.pkg`, has been built locally. Double-click to install into `/Applications`; Python and Node are bundled. The repository remains private and downloads are not published yet. The app is ad-hoc signed; the PKG is unsigned and not notarized. Frozen offline self-tests passed; native UI, permissions and clean-machine installation remain unverified. Intel builds and minimum supported macOS are not verified. Built on macOS 27.0.1. See [macOS build notes](docs/MACOS_BUILD.md).

### From source

Python 3.10+ and Node.js 18+ are required. Python 3.12 has been verified on Windows. Node runs the bundled local Zi Wei engine; npm installation is unnecessary at runtime.

```sh
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv/Scripts/python -m pip install -r requirements-desktop.txt
.venv/Scripts/python run_desktop.py
```

macOS:

```sh
.venv/bin/python -m pip install -r requirements-macos.txt
.venv/bin/python run_desktop.py
```

For the algorithms alone, use `python -m pip install .` and consult [the API guide](docs/ALGORITHMS.md).

<a id="privacy"></a>
<a id="ai"></a>

## Local records and optional AI

Charts, card draws, city search and birthday records are processed locally without an account. Birth information, current cities, notes, saved readings and preferences stay on your computer. The app has no background account sync or cloud database.

AI is optional. When you request an interpretation or follow-up, the relevant questions, chart information and conversation are sent to your configured LLM provider. That provider determines how it handles the data. API keys are not written to application preferences.

Two other optional features can use the network: system location, with your consent, and audio links you choose to play. You can disable location and use only local music. See [privacy details and storage locations](docs/PRIVACY.md).

## Development and contributing

Mystery uses Three.js, pywebview, Python and SQLite. The core calculation modules can be used independently of the desktop interface.

- [API and calculation rules](docs/ALGORITHMS.md)
- [Build and release guide](docs/RELEASING.md)
- [Validation scope](docs/VALIDATION_0.11.1.md): 128 Python offline tests and nine frontend check scripts
- [Contributing](CONTRIBUTING.md)
- [Third-party sources and notices](THIRD_PARTY_NOTICES.md)

Run Python checks with `python scripts/check_desktop.py`. Frontend checks are in `scripts/check_*.mjs`.

Original project code and documentation are licensed under [AGPL-3.0-only](LICENSE), copyright SaSa (SamanthaMengjunyu). Third-party components retain their own licenses; see [COPYRIGHT](COPYRIGHT) and [third-party notices](THIRD_PARTY_NOTICES.md). For future releases, see the [GitHub publishing guide](docs/GITHUB_PUBLISH.md).

## About me

I'm **SaSa**. I work on AI products and build things I want to use in my spare time. I currently work on multimodal AI projects for the entertainment industry at [Quwan Qianyin (AllVoiceLab)](https://www.allvoicelab.cn/) — feel free to visit [our team site](https://www.allvoicelab.cn/). An open-source project of my own is also coming soon — stay tuned ✨

If something doesn't work, or you have an idea for something fun to add, feel free to open an issue. Please replace personal birthdays or conversations with fictional examples before sharing them.

[GitHub](https://github.com/SamanthaMengjunyu) · [My interactive desk](https://samanthamengjunyu.github.io/Samantha-creative.github.io/) · [Quwan Qianyin AllVoiceLab](https://www.allvoicelab.cn/)
