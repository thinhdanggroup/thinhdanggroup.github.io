---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        -   label: "Linkedin"
            icon: "fab fa-fw fa-linkedin"
            url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image:  /assets/images/merging-audio/banner.jpg
    overlay_filter: 0.5
    teaser:  /assets/images/merging-audio/banner.jpg
title: "Building a Conference Audio Call System"
tags:
    - Audio Processing

---

# How to Build a Conference Call System: Mixing Voices Made Simple

Imagine you’re chatting with friends over a group call. You hear everyone’s voices blending together smoothly, without your own voice echoing back at you. Pretty cool, right? But behind that seamless experience, there’s a lot going on. In this blog, I’ll walk you through how to build a conference call system that collects voices from multiple people, mixes them together, and sends the right sound back to each person—all in real-time. We’ll focus on the tricky bits, like combining voices and making sure everything sounds clear, and I’ll share the techniques I used to make it work.

## What’s a Conference Call System Anyway?

A conference call system lets a bunch of people talk to each other at the same time, no matter where they are. Here’s how it works in simple terms:

- Each person speaks into their device (like a phone or computer).
- Their voice gets sent to a central computer (called a server).
- The server mixes all the voices together and sends the combined sound back to everyone.

But here’s the catch: if you hear your own voice in the mix, it sounds like an annoying echo. So, the system has to be smart—it mixes only the *other* people’s voices for you and leaves yours out. That’s the magic we’re building!

## The Big Pieces of the Puzzle

Our system has three main parts:

1. **The Client**: This is the app or program on your device. It grabs your voice and sends it to the server, then plays the mixed audio it gets back.
2. **The Server**: Think of this as the middleman. It uses a tool called WebSockets to keep a fast, open line of communication with everyone’s devices.
3. **The Conference Service**: This is the brain that does the heavy lifting—mixing voices and deciding who hears what.

Let’s dive into the Conference Service, because that’s where the real action happens.

## Inside the Conference Service: How It Works

The Conference Service is like a busy chef in a kitchen, juggling these three jobs:

1. **Tracking Who’s Here**: It keeps a list of everyone in the call, adding new people when they join and removing them when they leave.
2. **Grabbing Voices**: It collects everyone’s voice as little audio snippets (called chunks).
3. **Mixing and Sending**: It blends those snippets into a custom mix for each person and sends it back.

To pull this off, I used a few handy tricks:

- **Queues**: These are like organized lines where audio snippets wait their turn to be processed. Each person gets their own queues for sending and receiving audio.
- **Asynchronous Programming**: This lets the system handle lots of tasks at once—like cooking multiple dishes without burning anything—using Python’s `asyncio`.
- **NumPy**: A tool that’s great at math, which I used to mix audio quickly and cleanly.

## How Voices Travel Through the System

Let’s follow a voice from your mouth to your friends’ ears:

1. **You Speak**: Your device records your voice, turns it into a special format (base64-encoded mu-law audio), and sends it to the server via WebSocket.
2. **Server Gets It**: The server catches your voice and hands it to the Conference Service.
3. **Mixing Happens**: The Conference Service decodes your voice, mixes it with others (but not for you!), and prepares a unique mix for each person.
4. **Friends Hear**: Each person’s device gets their mix and plays it—everyone hears the group, minus their own voice.

## The Star of the Show: Mixing Voices

Mixing voices is like being a DJ at a party—you’ve got to blend different sounds without making a mess. Here’s how I did it, step by step, with techniques I applied:

### Step 1: Collecting Audio Snippets

Every voice gets split into tiny pieces called chunks. Each chunk has a timestamp, like a little clock saying when it was recorded. Imagine these as notes in a song—you need to know when each one hits.

### Step 2: Timing It Right

I check if the chunks from different people happened close enough together (within 30 milliseconds, or 0.03 seconds). If they’re in sync, I mix them. If not, I handle them one at a time to avoid weird gaps or overlaps.

**Technique**: *Timestamp Checking*  
Think of it like lining up dancers for a group routine. If they’re all on the same beat, they dance together. If one’s late, they wait their turn. Here’s a peek at how I coded it:

```python
def should_mix_chunks(chunks):
    timestamps = [chunk.timestamp for chunk in chunks if chunk]
    if len(timestamps) <= 1:
        return False
    time_diff = max(timestamps) - min(timestamps)
    return time_diff <= 30_000_000  # 30 milliseconds in nanoseconds
```

### Step 3: Making Custom Mixes

For every person, I create a mix with everyone *else’s* voices, skipping their own to stop that pesky echo.

**Technique**: *Echo Cancellation*  
Picture yourself in a room with friends. You want to hear them talk, not your own voice bouncing off the walls. In code, I just leave out your chunk:

```python
# For person at position i, skip their chunk
mix_without_me = chunks[:i] + chunks[i + 1:]
```

### Step 4: Blending the Audio

Here’s where the mixing happens:

- Take all the chunks I want to mix.
- Make them the same length by adding silence to shorter ones (like filling empty space in a playlist).
- Add them together using NumPy.
- Lower the volume a bit so it doesn’t get too loud and crackly (called normalization).

**Technique**: *Audio Summing and Normalization*  
It’s like layering cake flavors—you combine them, then smooth out the taste so it’s not overwhelming. Here’s a simplified version:

```python
import numpy as np

def mix_audio(chunks):
    max_length = max(len(chunk) for chunk in chunks)
    padded_chunks = [np.pad(chunk, (0, max_length - len(chunk)), "constant") for chunk in chunks]
    mixed = np.sum(padded_chunks, axis=0)  # Add them up
    mixed = mixed / len(chunks)  # Lower the volume
    return np.clip(mixed, -32768, 32767).astype(np.int16)  # Keep it in range
```

### Step 5: Skipping Silence

If someone’s not talking, their chunk is just silence. I check for that and leave it out to keep the mix crisp.

**Technique**: *Silence Detection*  
Think of it like muting a microphone when no one’s singing. I measure the “energy” of the sound and skip it if it’s too quiet:

```python
def is_silent(chunk):
    energy = np.sum(chunk.astype(np.float32) ** 2)
    return energy <= 5000  # My threshold for “quiet”
```

## A Real-Life Example: Three Friends on a Call

Let’s see this in action with Amy, Ben, and Charlie on a call:

- **Amy says “Hi!”**: Her device sends a chunk (timestamp: 1.0s).
- **Ben says “Hey!”**: His chunk arrives (timestamp: 1.01s).
- **Charlie’s quiet**: His chunk is silent (timestamp: 1.02s).

The Conference Service:
1. Checks timestamps: 1.0 and 1.01 are close (0.01s apart < 0.03s), so they mix; Charlie’s is silent, so it’s skipped.
2. For Amy: Mixes Ben’s “Hey!” (no “Hi!”).
3. For Ben: Mixes Amy’s “Hi!” (no “Hey!”).
4. For Charlie: Mixes Amy’s “Hi!” and Ben’s “Hey!”.
5. Sends each mix back.

Result: Amy hears “Hey!”, Ben hears “Hi!”, and Charlie hears both—no echoes, all clear!

## Switching Audio Formats

Voices need to change “outfits” as they move through the system:
- **From Device to Server**: Packed as base64 mu-law (small and fast for WebSocket).
- **For Mixing**: Unpacked to PCM audio and NumPy arrays (easy to work with).
- **Back to Device**: Repacked as base64 mu-law.

I built a helper called `TwilioTranslator` to handle this. It’s like a wardrobe manager swapping clothes:

```python
class TwilioTranslator:
    def to_array(self, base64_audio):
        mulaw = base64.b64decode(base64_audio)
        pcm = audioop.ulaw2lin(mulaw, 2)  # 2-byte samples
        return np.frombuffer(pcm, dtype=np.int16)

    def to_base64(self, array):
        pcm = array.tobytes()
        mulaw = audioop.lin2ulaw(pcm, 2)
        return base64.b64encode(mulaw).decode("utf-8")
```

## Keeping Track of People

Each person gets a `ConferenceStreamService` object—like a personal assistant managing their audio queues:
- **Input Queue**: Where their voice arrives.
- **Mixing Queue**: Where it waits to be blended.
- **Output Queue**: Where their custom mix goes.

When Amy joins, I make one for her. When she leaves, I toss it out. Simple!

## Hooking It Up to the Server

The server uses FastAPI and WebSockets. When someone connects:
1. They send a “start” message with an ID.
2. The server adds them to the Conference Service.
3. Audio flows in, gets mixed, and flows out.
4. They send “stop” when they’re done, and they’re removed.

## Testing with a Fake Client

I made a mock client to test this:
- Reads a WAV file (like a pre-recorded “Hello!”).
- Converts it to base64 mu-law.
- Sends it over WebSocket.
- Plays the mix it gets back.

It’s like a rehearsal before the real show!

## Bumps in the Road (and How I Fixed Them)

Building this wasn’t all smooth sailing. Here’s what I faced and how I tackled it:

1. **Delay (Latency)**: People hate waiting to hear each other.  
   - *Fix*: Used fast queues and `asyncio` to keep things zippy.

2. **Out-of-Sync Voices**: Voices need to match up in time.  
   - *Fix*: Checked timestamps to mix only synced chunks.

3. **Messy Sound**: Too many voices can get loud and distorted.  
   - *Fix*: Normalized the mix and skipped silent bits.

4. **Lots of People**: The system has to handle a crowd.  
   - *Fix*: Asynchronous programming let it multitask like a pro.

## Wrapping It All Up

Building a conference call system is like conducting an orchestra—everyone’s voice needs to play in harmony. Here’s what makes it tick:

- **Asynchronous Programming**: Handles many voices at once.
- **Queues**: Keeps audio organized.
- **NumPy**: Mixes voices fast and clean.
- **WebSockets**: Delivers sound in real-time.

The mixing part is the star—syncing voices, skipping echoes, and balancing sound. With this setup, you’ve got a solid base to add extras like recording or noise filtering. Now you’re ready to host your own virtual hangout!