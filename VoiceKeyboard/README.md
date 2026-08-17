# VoiceKeyboard — Local Voice-Model Inferencing Keyboard for Android

An Android IME (Input Method Editor) that performs **fully on-device** speech-to-text
using a gallery of quantised edge models. No data ever leaves the device.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                   VoiceInputMethodService (IME)               │
│  ┌───────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  KeyboardView │  │   AudioRecorder  │  │  VadEngine    │  │
│  │  (QWERTY +    │  │  (AudioRecord,   │  │  (Silero VAD  │  │
│  │   voice bar)  │  │   16 kHz mono)   │  │   ONNX)       │  │
│  └───────┬───────┘  └────────┬─────────┘  └──────┬────────┘  │
│          │                   │ raw PCM            │ gate      │
│          │            ┌──────▼────────────────────▼───────┐   │
│          │            │         InferenceEngine            │   │
│          │            │  ┌──────────────┐  ┌───────────┐  │   │
│          │            │  │ TFLite path  │  │ ONNX path │  │   │
│          │            │  │ (GPU/NNAPI)  │  │ (OrtEnv)  │  │   │
│          │            │  └──────────────┘  └───────────┘  │   │
│          │            │  AudioPreprocessor (log-Mel STFT)  │   │
│          │            └────────────────────────────────────┘   │
│          │                         │ transcript                │
│          └─────────────────────────▼──────────────────────     │
│                       InputConnection.commitText()             │
└───────────────────────────────────────────────────────────────┘
```

## Edge Model Gallery

| Model | Backend | Size | Language | Quality | RTF |
|---|---|---|---|---|---|
| Whisper Tiny EN | TFLite INT8 | 39 MB | English | Fair | 0.08× |
| Whisper Base EN | TFLite INT8 | 74 MB | English | Good | 0.15× |
| Whisper Tiny Multi | ONNX INT8 | 44 MB | 99 langs | Fair | 0.10× |
| Whisper Base Multi | ONNX INT8 | 80 MB | 99 langs | Good | 0.20× |
| Silero VAD v4 | ONNX FP32 | 1.8 MB | — (gating) | — | 0.01× |

RTF = real-time factor on a mid-range ARM Cortex-A78.

## Key Features

- **Zero cloud dependency** — inference runs entirely on the Android device
- **Dual backend** — TensorFlow Lite (GPU delegate) *or* ONNX Runtime per model
- **VAD gating** — Silero VAD suppresses silence before Whisper inference runs
- **Log-Mel STFT** — native Kotlin FFT + Mel filterbank matching Whisper's expected input
- **Model Gallery UI** — pick, install, and switch models without restarting the keyboard
- **QWERTY keyboard** — full character input with shift, backspace (long-press = delete word), enter
- **Settings** — VAD threshold, haptic feedback, GPU toggle, auto-punctuate

## Project Structure

```
VoiceKeyboard/
├── app/src/main/
│   ├── AndroidManifest.xml
│   ├── assets/models/          ← drop .tflite / .onnx files here before build
│   ├── java/com/voicekeyboard/
│   │   ├── VoiceInputMethodService.kt  ← IME entry point
│   │   ├── inference/
│   │   │   ├── AudioPreprocessor.kt   ← log-Mel STFT (pure Kotlin)
│   │   │   ├── AudioRecorder.kt       ← 16 kHz mono PCM capture
│   │   │   ├── InferenceEngine.kt     ← TFLite / ONNX unified wrapper
│   │   │   └── VadEngine.kt           ← Silero VAD ONNX wrapper
│   │   ├── model/
│   │   │   ├── ModelGallery.kt        ← catalog + persistence
│   │   │   └── VoiceModel.kt          ← model data class
│   │   └── ui/
│   │       ├── KeyboardView.kt        ← QWERTY + voice action bar
│   │       ├── VoiceRippleView.kt     ← animated recording indicator
│   │       ├── MainActivity.kt        ← setup wizard
│   │       ├── ModelGalleryActivity.kt← model picker
│   │       └── SettingsActivity.kt    ← preferences
│   └── res/
│       ├── drawable/                  ← vector icons + key/button backgrounds
│       ├── layout/                    ← keyboard_root, key, rows, activities
│       ├── values/                    ← strings, colors, dimens, themes
│       └── xml/method.xml             ← IME subtype declaration
├── app/build.gradle.kts
├── gradle/libs.versions.toml
└── settings.gradle.kts
```

## Building

### 1 — Add model files

Convert your models to quantised TFLite / ONNX and place them in:

```
app/src/main/assets/models/
  whisper_tiny_en_int8.tflite
  whisper_base_en_int8.tflite
  whisper_tiny_multilingual.onnx
  whisper_base_multilingual.onnx
  silero_vad_v4.onnx
```

Pre-converted Whisper TFLite models are available from the
[whisper.tflite](https://github.com/usefulsensors/openai-whisper) project.
Silero VAD ONNX is available from [snakers4/silero-vad](https://github.com/snakers4/silero-vad).

### 2 — Build & install

```bash
./gradlew :app:installDebug
```

### 3 — Enable the keyboard

1. **Settings → General Management → Keyboard list and default → Voice Keyboard** ✓
2. Set *Voice Keyboard* as default input method
3. Open the Voice Keyboard app → tap **Model Gallery** → install a model

## Runtime Inference Flow

```
Mic (16 kHz mono PCM)
  │
  ▼  512-sample chunks
VAD (Silero) ── silence → discard
  │  voice
  ▼
Accumulate PCM buffer
  │  utterance end (1.5 s silence)
  ▼
AudioPreprocessor
  log-Mel spectrogram [80 × 3000]
  │
  ▼
InferenceEngine (TFLite GPU / ONNX)
  Whisper encoder–decoder
  │  token IDs
  ▼
BPE tokenizer → transcript string
  │
  ▼
InputConnection.commitText()
```

## Permissions

| Permission | Reason |
|---|---|
| `RECORD_AUDIO` | Microphone access for voice capture |
| `FOREGROUND_SERVICE` | Keeps inference session alive while keyboard is visible |

## Adding a Custom Model

1. Implement the model's input/output contract in `InferenceEngine.kt`
2. Add a `VoiceModel` entry to `ModelGallery.catalog`
3. Drop the model file in `assets/models/`
4. Rebuild

The engine currently expects:
- **Input**: `[1, 80, 3000]` float32 log-Mel spectrogram (TFLite) or `mel_input` tensor (ONNX)
- **Output**: token ID sequence decoded greedily
