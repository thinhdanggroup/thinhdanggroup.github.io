---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        - label: "Linkedin"
          icon: "fab fa-fw fa-linkedin"
          url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/how-a-language-model-learned-to-speak-vietnamese/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/how-a-language-model-learned-to-speak-vietnamese/banner.png
title: "How a Language Model Learned to Speak Vietnamese"
tags:
    - llm
    - tts
    - vietnamese
---

You've used Google Translate's voice feature. You know the one — you type something, hit the speaker icon, and hear a voice that is technically correct but somehow deeply wrong. It hits the right phonemes in the right order, but there's no life in it. No rhythm. And if the language is Vietnamese, there's a good chance it mispronounces the tones so badly that the sentence means something completely different from what you typed.

Text-to-speech feels like a solved problem in 2025. It isn't. And understanding *why* it isn't — and how the latest generation of models actually works — turns out to be one of the more interesting engineering stories of the last few years.

This post walks through the full stack: from the physics of sound to the architecture of modern LLM-based TTS systems. We'll use Vietnamese as our running example, because Vietnamese makes the hard problems obvious in a way that English doesn't.

By the end, you'll understand exactly why a bad TTS system says "ghost" when it meant to say "mother" — and how a language model fixes it.

---

## Sound Is Just Numbers. Except It Isn't.

Let's start at the bottom. When your microphone records audio, it samples air pressure thousands of times per second and converts each measurement to a number. That's it. A Vietnamese speaker saying "Xin chào" becomes an array of 72,000 floats (3 seconds at 24,000 samples per second).

```python
import librosa

y, sr = librosa.load("xin_chao.wav", sr=None)
print(y.shape)   # (72000,)
print(sr)        # 24000
print(y[:5])     # [ 0.0012, -0.0034,  0.0021, -0.0008,  0.0019]
```

Simple enough. Now try to do anything useful with those 72,000 numbers.

The problem is that everything interesting about speech — pitch, vowels, consonants, tone — is *entangled* in this flat array. The letter "a" in "chào" doesn't live at position 15,000. It's spread across thousands of samples, overlapping with adjacent phonemes, shaped by the speaker's vocal tract, colored by the recording room.

Before any machine learning can happen, you need a better representation. This is where the **Short-Time Fourier Transform (STFT)** enters the picture, and where most TTS tutorials gloss over something important.

The STFT doesn't compute one big Fourier transform over the whole signal. It slices the signal into overlapping windows of about 42ms each and computes the frequency content of each slice. The result is a 2D matrix — time on one axis, frequency on the other — called a **spectrogram**.

```python
n_fft = 1024       # FFT size → frequency resolution = 24000/1024 ≈ 23 Hz per bin
hop_length = 256   # step between windows → time resolution = 256/24000 ≈ 11ms per frame

D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
print(D.shape)  # (513, 281)  — 513 frequency bins × 281 time frames
```

Here's the catch that trips everyone up: there's a hard physical tradeoff hiding in those two numbers. A larger window gives you sharper frequency resolution but blurrier time resolution. A smaller window does the opposite. This isn't a software limitation — it's the **Heisenberg-Gabor uncertainty principle** for signals: you cannot simultaneously know *exactly* when something happened and *exactly* what frequency it was.

For Vietnamese speech, this matters. Vietnamese fundamental pitch (F0) spans 80–400 Hz, and you need frequency resolution of at least ~23 Hz to distinguish adjacent tones. But you also need time resolution of ~11ms to catch the sharp consonant closures and tone onset points. The choice `n_fft=1024, hop_length=256` at 24 kHz is the sweet spot — not arbitrary, not magic, but derived from the physics of the language.

From here, one more transformation gets us to the **mel spectrogram** — a version of the STFT where the frequency axis is compressed to match human perception. Humans are much better at distinguishing pitches in the 80–700 Hz range (where Vietnamese tones live) than in the 8,000–12,000 Hz range. The mel filterbank allocates more bins to the low end and fewer to the high end, which is exactly what a tone-sensitive model needs.

---

## The Six Tones Problem

Here's where Vietnamese becomes the most instructive language to study for TTS.

English is not tonal. The word "table" means "table" regardless of whether you say it with rising or falling pitch. Vietnamese has **six tones** (thanh điệu), each of which is a distinct phoneme. The syllable "ma" has six completely different meanings depending on pitch contour:

| Written | Tone name | Pitch shape               | Meaning        |
| ------- | --------- | ------------------------- | -------------- |
| ma      | ngang     | flat, high                | ghost          |
| mà      | huyền     | falling, breathy          | but / however  |
| má      | sắc       | rising                    | cheek / mother |
| mả      | hỏi       | dips then rises           | tomb           |
| mã      | ngã       | rising with glottal creak | horse / code   |
| mạ      | nặng      | low, falling, short       | rice seedling  |

A TTS model that gets the tone wrong doesn't produce accented speech. It produces *different words*. Say "má" with a falling tone and you've called someone's mother a "but." The stakes are unusually high.

What makes this hard computationally is that tone information is encoded in the **F0 contour** — the fundamental frequency trajectory over the duration of a syllable. To generate correct Vietnamese speech, a model must precisely control how pitch evolves over time, frame by frame.

This is why the mel spectrogram alone isn't enough for tone analysis. We also use **MFCCs with delta features** — the rate of change and acceleration of spectral coefficients — because tone information lives in the *dynamics*, not just the static shape of a phoneme.

```python
mfccs       = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
delta_mfcc  = librosa.feature.delta(mfccs, order=1)  # velocity: how fast is the spectrum changing?
delta2_mfcc = librosa.feature.delta(mfccs, order=2)  # acceleration: is that change speeding up?

# Tone fingerprints in delta features:
# ngang (flat):     delta[1] ≈ 0    — stable pitch, little change
# sắc (rising):    delta[1] > 0    — spectrum brightening as pitch climbs
# huyền (falling): delta[1] < 0    — spectrum darkening as pitch drops
# hỏi (dipping):  delta2[1] changes sign — falls then rises (inflection point)
# nặng (abrupt):  large negative spike at endpoint — fast deceleration
```

Older speech systems spent years building hand-crafted rules for Vietnamese tone modeling. The modern approach is more interesting — and the path to get there is worth understanding.

---

## Twenty Years of TTS Architecture in Five Minutes

To appreciate why the current generation of TTS models works the way it does, it helps to know what came before.

**Concatenative synthesis** (late 1990s–2010s) worked by stitching together pre-recorded audio fragments from a large database. Results were natural when they worked — but they couldn't generalize. Recording a Vietnamese voice in every tone, in every phonetic context, required thousands of hours of studio time. Stitching artifacts were obvious to any native listener.

**HMM-based synthesis** replaced the database with statistical models of speech. More flexible, but the output had that unmistakable "robot reading" quality — smooth in a way human speech isn't, missing the micro-variations that make voice feel alive.

**Tacotron 2** (Google, 2017) was the first deep learning system to produce genuinely natural-sounding speech at scale. It uses an encoder-decoder with attention to predict mel spectrograms from text. A separate neural vocoder (WaveNet, then HiFi-GAN) converts the spectrogram back to audio. For Vietnamese, the attention mechanism is particularly tricky — the model must learn tone-phoneme alignments where one character carries dramatically different phonetic weight depending on its diacritics.

**FastSpeech 2** dropped the attention mechanism and replaced it with a duration predictor — a small network that explicitly predicts how long each phoneme should last. Faster, more stable, but the duration model still struggles with Vietnamese's tone-triggered length variations (the tone `nặng` systematically shortens syllable duration in ways that are hard to predict without phonemic context).

Then something shifted.

---

## The Insight: Speech Is Just Another Language

The latest generation of TTS systems — including VieNeu-TTS, which is the model at the center of this course — is built on a realization that sounds obvious in retrospect: if you can quantize speech into discrete tokens, a language model can learn to generate speech the same way it generates text.

This is how it works.

### Step 1 — The Neural Codec

A neural audio codec (NeuCodec) is trained to compress audio into a sequence of integer tokens using **Residual Vector Quantization (RVQ)**. Think of it as a very aggressive audio compression scheme that, instead of FLAC or MP3, produces a short sequence of integer codes from a learned codebook.

At each level of the RVQ stack, a codebook of 1,024 vectors is learned. The first codebook captures coarse structure (pitch, energy, broad phoneme shape). Each subsequent codebook refines the residual error. The codec encodes audio at 50 tokens per second — a 5-second clip becomes just 250 integers.

```python
from neucodec import DistillNeuCodec
import torch

codec = DistillNeuCodec.from_pretrained("neuphonic/distill-neucodec").eval()

# A 5-second Vietnamese audio clip
wav = torch.from_numpy(audio_array).float().unsqueeze(0).unsqueeze(0)

with torch.no_grad():
    codes = codec.encode_code(wav)  # shape: [1, 1, 250]

print(codes.shape)    # torch.Size([1, 1, 250])
print(codes[0, 0, :8])
# tensor([412, 87, 634, 201, 559, 38, 701, 92])
# — a sequence of integers that encodes the audio
```

These integers are meaningless to us, but they are everything to the model. The codec decoder can reconstruct high-quality 24 kHz audio from them alone, with tone contours and speaker characteristics intact.

### Step 2 — The Language Model

A causal transformer is trained on sequences that interleave text tokens and speech tokens:

```
[BOS] [text: "Xin chào"] [SEP] [ref speech: 412, 87, 634, ...] [SEP] [target speech: ???]
```

The model learns to predict target speech tokens autoregressively, conditioned on both the text prompt and a reference voice sample. Vietnamese tone modeling falls out of this naturally: the model has seen millions of Vietnamese examples during training and has learned that the phoneme sequence for "chào" should produce codec tokens corresponding to a falling-then-low F0 contour.

The loss is just cross-entropy over the vocabulary of speech tokens — the same objective used to train any language model, applied to a vocabulary of 1,024 audio codes instead of 50,000 words.

### Step 3 — Decoding

The predicted token sequence goes back through the codec decoder, which reconstructs the audio waveform directly. No separate vocoder. No mel spectrogram predicted explicitly. The codec decoder handles phase reconstruction internally through its learned decoder network.

```python
from vieneu import Vieneu

tts = Vieneu()

# Standard inference — the model handles tone automatically
audio = tts.infer("Trí tuệ nhân tạo đang thay đổi thế giới.")

# Voice cloning — provide a 3–5 second reference clip
audio_cloned = tts.infer(
    text="Trí tuệ nhân tạo đang thay đổi thế giới.",
    ref_audio="speaker_reference.wav"
)
# Output is in the reference speaker's voice, with all six tones correct
```

---

## Zero-Shot Voice Cloning Falls Out for Free

This is the part that surprises people the most.

In the older Tacotron 2 / FastSpeech 2 paradigm, cloning a new voice required either fine-tuning the entire model on the new speaker's data, or training a speaker encoder to extract embeddings — both expensive, both requiring significant amounts of new data.

With the LLM approach, voice cloning is just **in-context learning**. The reference audio tokens in the prompt tell the model what the speaker sounds like. The model has learned, from its training data, to match output token statistics to the conditioning context. Provide a few seconds of a new speaker and the model transfers that speaker's characteristics to the generated speech — no fine-tuning, no speaker embeddings, no retraining.

```python
# These two calls produce speech in completely different voices
# using the same model, zero additional training

audio_north = tts.infer("Xin chào.", ref_audio="hanoi_speaker.wav")
audio_south = tts.infer("Xin chào.", ref_audio="saigon_speaker.wav")

# The model even handles regional dialect differences —
# Northern vs. Southern Vietnamese phonology, intonation patterns,
# and the distinct realizations of tones like ngã and hỏi
```

The underlying reason this works is that the model has learned to use the reference tokens as a "style prefix" — the same mechanism that allows a language model to mimic writing styles when given examples in the prompt.

---

## From Theory to Practice: The Course

Everything described above — the audio math, the architecture evolution, the codec-LLM pipeline, the fine-tuning and deployment — is covered in detail in the **[Vietnamese TTS Course](https://github.com/thinhdanggroup/vietnamese-tts-course)**, a free 10-chapter curriculum built around VieNeu-TTS.

Each chapter ships as a pair:
- A **theory document** (`.md`) — full math derivations, no handwaving, no "trust me on this"
- A **Jupyter notebook** (`.ipynb`) — runnable code with real Vietnamese audio examples

The course runs on Google Colab. Every notebook has a built-in setup cell — one click clones the repos, installs dependencies, and configures the environment.

```
Chapters 01–04  →  CPU is sufficient (signal processing, architectures, codecs)
Chapters 05–10  →  T4 GPU recommended (model inference, fine-tuning, deployment)
```

The progression follows the dependency graph naturally:

```
Audio Fundamentals → Text Processing → TTS Architectures → Neural Codecs
                                                                  ↓
                                                       LLM-Based TTS (VieNeu-TTS)
                                                       ↙                    ↘
                                              Voice Cloning            LoRA Fine-tuning
                                                                              ↓
                                                                      Data Preparation
                                                                              ↓
                                                                  Training & Evaluation
                                                                              ↓
                                                                         Deployment
```

The later chapters get into the practical engineering that most research papers skip: building a data quality pipeline with SNR filtering and tone distribution analysis, reading training loss curves to distinguish healthy convergence from overfitting, GGUF Q4 quantization math (why it's nearly lossless for TTS weights), streaming inference with overlap-add for low-latency conversational applications, and packaging a custom voice as a portable `voices.json` file for distribution.

---

## Key Takeaways

A few things worth carrying away from all of this:

**The representation problem is central, not peripheral.** Before any neural network architecture matters, you have to decide how to represent audio. The choice of spectrogram parameters — n_fft, hop_length, n_mels — is a consequence of the physics of the language being synthesized, not convention.

**Tonal languages expose what TTS models actually learn.** Vietnamese's six-tone system is a stress test for any synthesis system. A model that handles Vietnamese correctly has genuinely learned pitch dynamics, not just phoneme-to-waveform mapping. It's a useful benchmark for any tonal language: Mandarin, Thai, Cantonese, Yoruba.

**The LLM framing is a genuine paradigm shift, not a rebranding.** Treating speech tokens as a foreign language vocabulary isn't a metaphor — it's the actual implementation. Same transformer architecture, same cross-entropy loss, same autoregressive inference loop. The codec is the only new piece, and it is trained independently from the language model.

**Zero-shot voice cloning is a consequence of in-context learning, not a separate capability.** You don't need a dedicated cloning module. You need a good codec, a language model trained on diverse voices, and a prompt format that includes reference audio tokens.

**Deployment math matters more than most papers acknowledge.** Real-time factor, quantization tradeoffs, first-chunk latency — these determine whether a model is usable in a product. Chapter 10 benchmarks them concretely on real hardware.

---

## Further Reading

- **[VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS)** — the model the course is built around
- **[NeuPhonic NeuCodec](https://huggingface.co/neuphonic/distill-neucodec)** — the neural audio codec used for speech tokenization
- **Shen et al. (2018)** — "Natural TTS Synthesis by Conditioning WaveNet on Mel Spectrogram Predictions" (Tacotron 2)
- **Ren et al. (2021)** — "FastSpeech 2: Fast and High-Quality End-to-End Text to Speech"
- **Kim et al. (2021)** — "Conditional Variational Autoencoder with Adversarial Learning for End-to-End Text-to-Speech" (VITS)
- **Hu et al. (2022)** — "LoRA: Low-Rank Adaptation of Large Language Models"
- **[espeak-ng](https://github.com/espeak-ng/espeak-ng)** — the open-source phonemization backend used for Vietnamese G2P

---

*The course repository is at [github.com/thinhdanggroup/vietnamese-tts-course](https://github.com/thinhdanggroup/vietnamese-tts-course). Open any chapter notebook in Colab, run the setup cell, and you're running real Vietnamese TTS code in under two minutes.*
